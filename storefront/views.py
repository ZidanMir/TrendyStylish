import json
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum
from django.db.models.deletion import ProtectedError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import Coupon, CouponRedemption, CustomerProfile, Order, OrderItem, Product
from .services import (
    VerificationError,
    consume_signup_phone_verification,
    normalize_bangladesh_phone,
    send_email_verification_code,
    send_order_confirmation,
    send_order_status_update,
    send_phone_code,
    signup_phone_is_verified,
    verify_email_code,
    verify_phone_code,
)


@ensure_csrf_cookie
def storefront(request):
    return render(request, "index.html")


@staff_member_required(login_url="/admin/login/")
@ensure_csrf_cookie
def dashboard(request):
    return render(request, "dashboard.html")


@staff_member_required(login_url="/admin/login/")
def admin_entry(request):
    return redirect("dashboard")


def product_payload(product):
    if product.image:
        image_url = product.image.url
    elif product.static_image_path:
        image_url = staticfiles_storage.url(product.static_image_path)
    else:
        image_url = ""

    return {
        "id": product.slug,
        "name": product.name,
        "category": product.category,
        "price": product.price,
        "image": image_url,
        "tag": product.tag,
    }


@require_GET
def products_api(request):
    products = Product.objects.filter(is_active=True)
    return JsonResponse({"products": [product_payload(product) for product in products]})


def user_payload(user):
    profile = getattr(user, "customer_profile", None)
    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email,
        "name": user.get_full_name() or user.username,
        "phone": profile.phone if profile else "",
        "address": profile.address if profile else "",
        "phoneVerified": bool(profile and profile.phone_verified_at),
        "emailVerified": bool(profile and profile.email_verified_at),
    }


def order_payload(order):
    status_help = {
        Order.STATUS_PENDING: "Waiting for the shop to accept your order.",
        Order.STATUS_CONFIRMED: "The shop accepted your order and is preparing it.",
        Order.STATUS_RECEIVED: "Your delivery is complete.",
        Order.STATUS_CANCELLED: "This order was cancelled.",
    }
    return {
        "id": order.pk,
        "customerName": order.customer_name,
        "email": order.email,
        "phone": order.phone,
        "area": order.area,
        "address": order.address,
        "paymentMethod": order.payment_method,
        "subtotal": order.subtotal,
        "discount": order.discount,
        "deliveryFee": order.delivery_fee,
        "total": order.total,
        "coupon": order.coupon.code if order.coupon else "",
        "status": order.status,
        "statusLabel": order.get_status_display(),
        "statusHelp": status_help[order.status],
        "statusNote": order.status_note,
        "allowedStatuses": order.allowed_statuses(),
        "createdAt": order.created_at.isoformat(),
        "updatedAt": order.updated_at.isoformat(),
        "items": [
            {
                "name": item.product_name,
                "quantity": item.quantity,
                "unitPrice": item.unit_price,
                "lineTotal": item.line_total,
            }
            for item in order.items.all()
        ],
}


@require_POST
def phone_verification_send_api(request):
    try:
        payload = json.loads(request.body or "{}")
        phone = normalize_bangladesh_phone(payload.get("phone"))
        if CustomerProfile.objects.filter(phone__in={phone, f"0{phone[4:]}"}).exists():
            return JsonResponse({"error": "An account already exists with this phone number."}, status=400)
        phone, debug_code = send_phone_code(request.session, phone, payload.get("channel") or "sms")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    except VerificationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    response = {"phone": phone, "message": "Verification code sent."}
    if debug_code:
        response["debugCode"] = debug_code
    return JsonResponse(response)


@require_POST
def phone_verification_check_api(request):
    try:
        payload = json.loads(request.body or "{}")
        phone = verify_phone_code(request.session, payload.get("phone"), payload.get("code"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    except VerificationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"phone": phone, "verified": True})


@require_POST
def register_api(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    name = (payload.get("name") or "").strip()
    try:
        phone = normalize_bangladesh_phone(payload.get("phone"))
    except VerificationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    address = (payload.get("address") or "").strip()

    if not email or not password:
        return JsonResponse({"error": "Email and password are required."}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"error": "Enter a valid email address."}, status=400)
    if len(password) < 8:
        return JsonResponse({"error": "Password must be at least 8 characters."}, status=400)
    if not name:
        return JsonResponse({"error": "Enter your full name."}, status=400)
    if not signup_phone_is_verified(request.session, phone):
        return JsonResponse({"error": "Verify your phone number before creating the account."}, status=400)
    if User.objects.filter(username=email).exists():
        return JsonResponse({"error": "An account already exists with this email."}, status=400)
    phone_aliases = {phone, f"0{phone[4:]}"}
    if CustomerProfile.objects.filter(phone__in=phone_aliases).exists():
        return JsonResponse({"error": "An account already exists with this phone number."}, status=400)

    first_name, _, last_name = name.partition(" ")
    with transaction.atomic():
        user = User.objects.create_user(username=email, email=email, password=password, first_name=first_name, last_name=last_name)
        CustomerProfile.objects.create(user=user, phone=phone, phone_verified_at=timezone.now(), address=address)
    consume_signup_phone_verification(request.session)
    login(request, user)
    return JsonResponse({"user": user_payload(user)}, status=201)


@require_POST
def login_api(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    user = authenticate(request, username=email, password=password)
    if not user:
        return JsonResponse({"error": "Email or password is incorrect."}, status=400)

    CustomerProfile.objects.get_or_create(user=user)
    login(request, user)
    return JsonResponse({"user": user_payload(user)})


@require_POST
def logout_api(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
def me_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"user": None, "orders": []})

    orders = request.user.orders.select_related("coupon").prefetch_related("items")[:10]
    return JsonResponse({"user": user_payload(request.user), "orders": [order_payload(order) for order in orders]})


@require_POST
def email_verification_send_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Sign in before verifying email."}, status=401)
    profile, _created = CustomerProfile.objects.get_or_create(user=request.user)
    if profile.email_verified_at:
        return JsonResponse({"verified": True, "message": "Email is already verified."})
    try:
        debug_code = send_email_verification_code(request.session, request.user)
    except VerificationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    response = {"message": "Verification code sent to your email."}
    if debug_code:
        response["debugCode"] = debug_code
    return JsonResponse(response)


@require_POST
def email_verification_check_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Sign in before verifying email."}, status=401)
    CustomerProfile.objects.get_or_create(user=request.user)
    try:
        payload = json.loads(request.body or "{}")
        verify_email_code(request.session, request.user, payload.get("code"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    except VerificationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"verified": True, "user": user_payload(request.user)})


def staff_required_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Admin login required."}, status=401)
        if not request.user.is_staff:
            return JsonResponse({"error": "Staff access required."}, status=403)
        return view_func(request, *args, **kwargs)

    return wrapper


def dashboard_product_payload(product):
    payload = product_payload(product)
    payload.update(
        {
            "databaseId": product.pk,
            "isActive": product.is_active,
            "hasUploadedImage": bool(product.image),
            "sortOrder": product.sort_order,
            "staticImagePath": product.static_image_path,
            "updatedAt": product.updated_at.isoformat(),
        }
    )
    return payload


def dashboard_coupon_payload(coupon):
    redemption_count = getattr(coupon, "redemption_count", None)
    if redemption_count is None:
        redemption_count = coupon.redemptions.count()

    return {
        "id": coupon.pk,
        "code": coupon.code,
        "discountType": coupon.discount_type,
        "discountLabel": coupon.get_discount_type_display(),
        "value": coupon.value,
        "isActive": coupon.is_active,
        "singleUse": coupon.single_use_per_customer,
        "redemptions": redemption_count,
    }


def unique_product_slug(name, product_id=None):
    base = slugify(name) or "product"
    candidate = base
    suffix = 2
    existing = Product.objects.exclude(pk=product_id)
    while existing.filter(slug=candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def parse_nonnegative_int(value, label, minimum=0):
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a whole number.") from exc
    if number < minimum:
        raise ValueError(f"{label} must be at least {minimum}.")
    return number


@require_GET
@staff_required_json
def dashboard_overview_api(request):
    order_value = Order.objects.exclude(status=Order.STATUS_CANCELLED).aggregate(total=Sum("total"))["total"] or 0
    stats = {
        "orders": Order.objects.count(),
        "pending": Order.objects.filter(status=Order.STATUS_PENDING).count(),
        "products": Product.objects.filter(is_active=True).count(),
        "customers": User.objects.filter(is_staff=False).count(),
        "orderValue": order_value,
        "today": Order.objects.filter(created_at__date=timezone.localdate()).count(),
    }
    recent_orders = Order.objects.select_related("coupon").prefetch_related("items")[:5]
    return JsonResponse({"stats": stats, "recentOrders": [order_payload(order) for order in recent_orders]})


@require_GET
@staff_required_json
def dashboard_products_api(request):
    products = Product.objects.all()
    return JsonResponse({"products": [dashboard_product_payload(product) for product in products]})


@require_POST
@staff_required_json
def dashboard_product_create_api(request):
    name = (request.POST.get("name") or "").strip()
    category = request.POST.get("category")
    if not name:
        return JsonResponse({"error": "Product name is required."}, status=400)
    if category not in {choice[0] for choice in Product.CATEGORY_CHOICES}:
        return JsonResponse({"error": "Choose a valid product category."}, status=400)
    try:
        price = parse_nonnegative_int(request.POST.get("price"), "Price", minimum=1)
        sort_order = parse_nonnegative_int(request.POST.get("sortOrder") or 0, "Sort order")
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    product = Product.objects.create(
        slug=unique_product_slug(name),
        name=name,
        category=category,
        price=price,
        tag=(request.POST.get("tag") or "").strip(),
        image=request.FILES.get("image"),
        static_image_path=(request.POST.get("staticImagePath") or "").strip(),
        is_active=request.POST.get("isActive") == "true",
        sort_order=sort_order,
    )
    return JsonResponse({"product": dashboard_product_payload(product)}, status=201)


@require_POST
@staff_required_json
def dashboard_product_update_api(request, product_id):
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found."}, status=404)

    name = (request.POST.get("name") or "").strip()
    category = request.POST.get("category")
    if not name:
        return JsonResponse({"error": "Product name is required."}, status=400)
    if category not in {choice[0] for choice in Product.CATEGORY_CHOICES}:
        return JsonResponse({"error": "Choose a valid product category."}, status=400)
    try:
        price = parse_nonnegative_int(request.POST.get("price"), "Price", minimum=1)
        sort_order = parse_nonnegative_int(request.POST.get("sortOrder") or 0, "Sort order")
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    product.name = name
    product.slug = unique_product_slug(name, product.pk)
    product.category = category
    product.price = price
    product.tag = (request.POST.get("tag") or "").strip()
    product.static_image_path = (request.POST.get("staticImagePath") or "").strip()
    product.is_active = request.POST.get("isActive") == "true"
    product.sort_order = sort_order
    if request.FILES.get("image"):
        product.image = request.FILES["image"]
    if request.POST.get("removeImage") == "true":
        product.image = None
    product.save()
    return JsonResponse({"product": dashboard_product_payload(product)})


@require_POST
@staff_required_json
def dashboard_product_delete_api(request, product_id):
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found."}, status=404)
    try:
        product.delete()
    except ProtectedError:
        return JsonResponse(
            {"error": "This product belongs to an order. Hide it from the store instead."},
            status=400,
        )
    return JsonResponse({"deleted": True})


@require_GET
@staff_required_json
def dashboard_customers_api(request):
    customers = (
        User.objects.filter(is_staff=False)
        .select_related("customer_profile")
        .annotate(
            order_count=Count("orders"),
            order_total=Sum("orders__total", filter=~Q(orders__status=Order.STATUS_CANCELLED)),
        )
        .order_by("-date_joined")[:100]
    )
    result = []
    for customer in customers:
        profile = getattr(customer, "customer_profile", None)
        result.append(
            {
                "id": customer.pk,
                "name": customer.get_full_name() or customer.username,
                "email": customer.email,
                "phone": profile.phone if profile else "",
                "phoneVerified": bool(profile and profile.phone_verified_at),
                "emailVerified": bool(profile and profile.email_verified_at),
                "orders": customer.order_count,
                "orderTotal": customer.order_total or 0,
                "joinedAt": customer.date_joined.isoformat(),
            }
        )
    return JsonResponse({"customers": result})


@require_GET
@staff_required_json
def dashboard_coupons_api(request):
    coupons = Coupon.objects.annotate(redemption_count=Count("redemptions"))
    return JsonResponse({"coupons": [dashboard_coupon_payload(coupon) for coupon in coupons]})


def coupon_from_payload(coupon, payload):
    code = (payload.get("code") or "").strip().upper()
    discount_type = payload.get("discountType")
    if not code:
        raise ValueError("Coupon code is required.")
    if discount_type not in {choice[0] for choice in Coupon.DISCOUNT_CHOICES}:
        raise ValueError("Choose a valid discount type.")
    value = parse_nonnegative_int(payload.get("value"), "Discount", minimum=1)
    if discount_type == Coupon.DISCOUNT_PERCENT and value > 100:
        raise ValueError("Percentage discount cannot exceed 100.")
    duplicate = Coupon.objects.filter(code__iexact=code)
    if coupon:
        duplicate = duplicate.exclude(pk=coupon.pk)
    if duplicate.exists():
        raise ValueError("A coupon with this code already exists.")

    coupon = coupon or Coupon()
    coupon.code = code
    coupon.discount_type = discount_type
    coupon.value = value
    coupon.is_active = bool(payload.get("isActive"))
    coupon.single_use_per_customer = bool(payload.get("singleUse"))
    coupon.save()
    return coupon


@require_POST
@staff_required_json
def dashboard_coupon_create_api(request):
    try:
        payload = json.loads(request.body or "{}")
        coupon = coupon_from_payload(None, payload)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    coupon.redemption_count = 0
    return JsonResponse({"coupon": dashboard_coupon_payload(coupon)}, status=201)


@require_POST
@staff_required_json
def dashboard_coupon_update_api(request, coupon_id):
    try:
        coupon = Coupon.objects.annotate(redemption_count=Count("redemptions")).get(pk=coupon_id)
        payload = json.loads(request.body or "{}")
        coupon = coupon_from_payload(coupon, payload)
    except Coupon.DoesNotExist:
        return JsonResponse({"error": "Coupon not found."}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"coupon": dashboard_coupon_payload(coupon)})


@require_GET
@staff_required_json
def dashboard_orders_api(request):
    status = request.GET.get("status")
    valid_statuses = {choice[0] for choice in Order.STATUS_CHOICES}
    if status and status not in valid_statuses:
        return JsonResponse({"error": "Choose a valid order status."}, status=400)

    orders = Order.objects.select_related("coupon", "user").prefetch_related("items")
    if status:
        orders = orders.filter(status=status)

    stats = {
        "pending": Order.objects.filter(status=Order.STATUS_PENDING).count(),
        "confirmed": Order.objects.filter(status=Order.STATUS_CONFIRMED).count(),
        "received": Order.objects.filter(status=Order.STATUS_RECEIVED).count(),
        "cancelled": Order.objects.filter(status=Order.STATUS_CANCELLED).count(),
    }
    return JsonResponse({"orders": [order_payload(order) for order in orders[:50]], "stats": stats})


@require_POST
@staff_required_json
def dashboard_order_status_api(request, order_id):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    status = payload.get("status")
    if status not in {Order.STATUS_CONFIRMED, Order.STATUS_RECEIVED, Order.STATUS_CANCELLED}:
        return JsonResponse({"error": "Choose a valid status action."}, status=400)

    try:
        order = Order.objects.prefetch_related("items").select_related("coupon").get(pk=order_id)
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found."}, status=404)

    try:
        with transaction.atomic():
            order.set_status(status, user=request.user, note=(payload.get("note") or "").strip())
            transaction.on_commit(lambda: send_order_status_update(order))
    except ValueError:
        return JsonResponse(
            {"error": f"Order #{order.pk} cannot move from {order.get_status_display()} to that status."},
            status=400,
        )
    return JsonResponse({"order": order_payload(order)})


@require_POST
def orders_api(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    items = payload.get("items") or []
    if not isinstance(items, list) or not items:
        return JsonResponse({"error": "Add at least one product before checkout."}, status=400)

    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "Sign in before placing an order so updates can be sent to your registered email."},
            status=401,
        )

    profile, _created = CustomerProfile.objects.get_or_create(user=request.user)
    customer_name = (payload.get("name") or "").strip()
    email = request.user.email.strip().lower()
    phone_mode = payload.get("deliveryPhoneMode") or "custom"
    phone_value = payload.get("deliveryPhone") or payload.get("phone")
    if phone_mode == "registered":
        phone_value = profile.phone
        if not phone_value:
            return JsonResponse({"error": "Add a delivery number or choose another delivery number."}, status=400)
    elif phone_mode != "custom":
        return JsonResponse({"error": "Choose a delivery phone number."}, status=400)
    try:
        phone = normalize_bangladesh_phone(phone_value)
    except VerificationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    address = (payload.get("address") or "").strip()
    if not customer_name:
        return JsonResponse({"error": "Enter the customer name."}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"error": "Your account needs a valid email address for order updates."}, status=400)
    if not address:
        return JsonResponse({"error": "Enter the delivery address."}, status=400)

    product_ids = [item.get("id") for item in items if isinstance(item, dict)]
    if len(product_ids) != len(items) or len(set(product_ids)) != len(product_ids):
        return JsonResponse({"error": "Cart items are invalid."}, status=400)
    products = Product.objects.filter(slug__in=product_ids, is_active=True)
    product_by_slug = {product.slug: product for product in products}

    subtotal = 0
    order_items = []
    for item in items:
        product = product_by_slug.get(item.get("id"))
        try:
            quantity = int(item.get("quantity") or 0)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Cart quantity is invalid."}, status=400)
        if not product or quantity < 1 or quantity > 99:
            return JsonResponse({"error": "Cart contains an unavailable product."}, status=400)

        line_total = product.price * quantity
        subtotal += line_total
        order_items.append((product, quantity, line_total))

    area = payload.get("area")
    payment_method = payload.get("paymentMethod")
    if area not in {Order.AREA_INSIDE, Order.AREA_OUTSIDE}:
        return JsonResponse({"error": "Choose a valid delivery area."}, status=400)
    if payment_method not in {Order.PAYMENT_BKASH, Order.PAYMENT_COD}:
        return JsonResponse({"error": "Choose a valid payment method."}, status=400)

    coupon = None
    discount = 0
    coupon_code = (payload.get("couponCode") or "").strip().upper()
    if coupon_code:
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Sign in before redeeming a coupon."}, status=401)

        coupon = Coupon.objects.filter(code__iexact=coupon_code, is_active=True).first()
        if not coupon:
            return JsonResponse({"error": "Coupon is invalid or inactive."}, status=400)
        if coupon.single_use_per_customer and CouponRedemption.objects.filter(coupon=coupon, user=request.user).exists():
            return JsonResponse({"error": "You have already used this coupon."}, status=400)

        discount = coupon.calculate_discount(subtotal)

    delivery_fee = 70 if area == Order.AREA_INSIDE else 130
    try:
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                customer_name=customer_name,
                email=email,
                phone=phone,
                area=area,
                address=address,
                payment_method=payment_method,
                coupon=coupon,
                discount=discount,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                total=subtotal - discount + delivery_fee,
            )

            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=product,
                        product_name=product.name,
                        unit_price=product.price,
                        quantity=quantity,
                        line_total=line_total,
                    )
                    for product, quantity, line_total in order_items
                ]
            )

            if profile:
                profile.address = order.address
                profile.save(update_fields=["address"])

            if coupon and request.user.is_authenticated:
                CouponRedemption.objects.create(coupon=coupon, user=request.user, order=order, discount=discount)
            transaction.on_commit(lambda: send_order_confirmation(order))
    except IntegrityError:
        return JsonResponse({"error": "You have already used this coupon."}, status=400)

    return JsonResponse(
        {
            "id": order.pk,
            "paymentMethod": order.payment_method,
            "subtotal": order.subtotal,
            "discount": order.discount,
            "deliveryFee": order.delivery_fee,
            "total": order.total,
            "coupon": order.coupon.code if order.coupon else "",
            "status": order.status,
            "statusLabel": order.get_status_display(),
            "message": "Order placed. Confirmation and tracking updates will be sent to your registered email.",
        },
        status=201,
    )
