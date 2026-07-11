from django.contrib import admin

from .models import Coupon, CouponRedemption, CustomerProfile, Order, OrderItem, Product

admin.site.site_header = "Trendy Stylishness Admin"
admin.site.site_title = "Store Admin"
admin.site.index_title = "Store management"


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_active", "sort_order")
    list_filter = ("category", "is_active")
    list_editable = ("price", "is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "tag")
    save_on_top = True
    actions = ("show_in_store", "hide_from_store")

    @admin.action(description="Show selected products in store")
    def show_in_store(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="Hide selected products from store")
    def hide_from_store(self, request, queryset):
        queryset.update(is_active=False)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "created_at")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name", "phone")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount_type", "value", "is_active", "single_use_per_customer")
    list_filter = ("discount_type", "is_active", "single_use_per_customer")
    search_fields = ("code",)


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "user", "order", "discount", "created_at")
    list_filter = ("coupon", "created_at")
    search_fields = ("coupon__code", "user__username", "user__email")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "quantity", "line_total")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "user", "phone", "status", "payment_method", "coupon", "discount", "total", "created_at")
    list_filter = ("status", "payment_method", "area", "coupon", "created_at")
    search_fields = ("customer_name", "phone", "address", "user__username", "user__email")
    readonly_fields = (
        "user",
        "customer_name",
        "phone",
        "area",
        "address",
        "payment_method",
        "coupon",
        "subtotal",
        "delivery_fee",
        "discount",
        "total",
        "status",
        "status_note",
        "confirmed_by",
        "confirmed_at",
        "created_at",
        "updated_at",
    )
    inlines = [OrderItemInline]

    def has_add_permission(self, request):
        return False
