import json
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import Coupon, CouponRedemption, CustomerProfile, Order, OrderItem, Product


@ensure_csrf_cookie
def storefront(request):
    return render(request, "index.html")


@staff_member_required(login_url="/admin/login/")
@ensure_csrf_cookie
def dashboard(request):
    return render(request, "dashboard.html")


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
def register_api(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()
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
    if User.objects.filter(username=email).exists():
        return JsonResponse({"error": "An account already exists with this email."}, status=400)

    first_name, _, last_name = name.partition(" ")
    user = User.objects.create_user(username=email, email=email, password=password, first_name=first_name, last_name=last_name)
    CustomerProfile.objects.create(user=user, phone=phone, address=address)
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


def staff_required_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Admin login required."}, status=401)
        if not request.user.is_staff:
            return JsonResponse({"error": "Staff access required."}, status=403)
        return view_func(request, *args, **kwargs)

    return wrapper


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
        order.set_status(status, user=request.user, note=(payload.get("note") or "").strip())
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

    customer_name = (payload.get("name") or "").strip()
    phone = (payload.get("phone") or "").strip()
    address = (payload.get("address") or "").strip()
    if not customer_name:
        return JsonResponse({"error": "Enter the customer name."}, status=400)
    if len(phone) < 8:
        return JsonResponse({"error": "Enter a valid phone number."}, status=400)
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

            if request.user.is_authenticated:
                profile, _created = CustomerProfile.objects.get_or_create(user=request.user)
                profile.phone = order.phone
                profile.address = order.address
                profile.save(update_fields=["phone", "address"])

            if coupon and request.user.is_authenticated:
                CouponRedemption.objects.create(coupon=coupon, user=request.user, order=order, discount=discount)
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
            "message": "Order placed. The shop will review and confirm it.",
        },
        status=201,
    )
