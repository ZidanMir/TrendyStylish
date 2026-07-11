from django.conf import settings
from django.db import models
from django.utils import timezone


class Product(models.Model):
    CATEGORY_CARDS = "cards"
    CATEGORY_ACCESSORIES = "accessories"
    CATEGORY_STATIONERY = "stationery"

    CATEGORY_CHOICES = [
        (CATEGORY_CARDS, "Cards"),
        (CATEGORY_ACCESSORIES, "Accessories"),
        (CATEGORY_STATIONERY, "Stationery"),
    ]

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
    price = models.PositiveIntegerField(help_text="Price in Bangladeshi taka")
    tag = models.CharField(max_length=80, blank=True)
    image = models.ImageField(upload_to="products/", blank=True)
    static_image_path = models.CharField(
        max_length=180,
        blank=True,
        help_text="Fallback static path, for example assets/cards-party-pack.png",
    )
    is_active = models.BooleanField("Visible in store", default=True)
    sort_order = models.PositiveIntegerField(default=0, help_text="Lower numbers appear first")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="customer_profile", on_delete=models.CASCADE)
    phone = models.CharField(max_length=24, blank=True, db_index=True)
    phone_verified_at = models.DateTimeField(blank=True, null=True)
    email_verified_at = models.DateTimeField(blank=True, null=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Coupon(models.Model):
    DISCOUNT_PERCENT = "percent"
    DISCOUNT_FIXED = "fixed"

    DISCOUNT_CHOICES = [
        (DISCOUNT_PERCENT, "Percentage"),
        (DISCOUNT_FIXED, "Fixed amount"),
    ]

    code = models.CharField(max_length=32, unique=True)
    discount_type = models.CharField(max_length=12, choices=DISCOUNT_CHOICES, default=DISCOUNT_PERCENT)
    value = models.PositiveIntegerField(help_text="Percent or taka amount, based on discount type")
    is_active = models.BooleanField(default=True)
    single_use_per_customer = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code

    def calculate_discount(self, subtotal):
        if self.discount_type == self.DISCOUNT_FIXED:
            return min(self.value, subtotal)
        return min((subtotal * self.value) // 100, subtotal)


class Order(models.Model):
    PAYMENT_BKASH = "bkash"
    PAYMENT_COD = "cod"

    PAYMENT_CHOICES = [
        (PAYMENT_BKASH, "bKash"),
        (PAYMENT_COD, "Cash on delivery"),
    ]

    AREA_INSIDE = "inside"
    AREA_OUTSIDE = "outside"

    AREA_CHOICES = [
        (AREA_INSIDE, "Inside Dhaka"),
        (AREA_OUTSIDE, "Outside Dhaka"),
    ]

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_RECEIVED = "received"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_RECEIVED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name="orders", on_delete=models.SET_NULL)
    customer_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=24)
    area = models.CharField(max_length=16, choices=AREA_CHOICES)
    address = models.TextField()
    payment_method = models.CharField(max_length=16, choices=PAYMENT_CHOICES)
    coupon = models.ForeignKey(Coupon, blank=True, null=True, on_delete=models.SET_NULL)
    discount = models.PositiveIntegerField(default=0)
    subtotal = models.PositiveIntegerField(default=0)
    delivery_fee = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    status_note = models.CharField(max_length=180, blank=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        related_name="confirmed_orders",
        on_delete=models.SET_NULL,
    )
    confirmed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    STATUS_TRANSITIONS = {
        STATUS_PENDING: (STATUS_CONFIRMED, STATUS_CANCELLED),
        STATUS_CONFIRMED: (STATUS_RECEIVED, STATUS_CANCELLED),
        STATUS_RECEIVED: (),
        STATUS_CANCELLED: (),
    }

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} - {self.customer_name}"

    def allowed_statuses(self):
        return list(self.STATUS_TRANSITIONS.get(self.status, ()))

    def set_status(self, status, user=None, note=""):
        if status not in self.STATUS_TRANSITIONS.get(self.status, ()):
            raise ValueError(f"Order cannot change from {self.get_status_display()} to {status}.")

        self.status = status
        self.status_note = note
        if status == self.STATUS_CONFIRMED:
            self.confirmed_by = user
            self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "status_note", "confirmed_by", "confirmed_at", "updated_at"])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=120)
    unit_price = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    line_total = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class CouponRedemption(models.Model):
    coupon = models.ForeignKey(Coupon, related_name="redemptions", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="coupon_redemptions", on_delete=models.CASCADE)
    order = models.OneToOneField(Order, related_name="coupon_redemption", on_delete=models.CASCADE)
    discount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("coupon", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} redeemed {self.coupon}"
