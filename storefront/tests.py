import json

from django.contrib.auth.models import User
from django.test import TestCase

from .models import Coupon, CouponRedemption, Order, Product


class StorefrontApiTests(TestCase):
    def test_products_api_returns_seeded_products(self):
        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["products"]), 4)
        self.assertEqual(payload["products"][0]["id"], "party-cards")

    def test_products_api_does_not_restore_hidden_products(self):
        Product.objects.update(is_active=False)

        response = self.client.get("/api/products/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["products"], [])

    def test_orders_api_saves_order_items_from_current_prices(self):
        product = Product.objects.get(slug="party-cards")
        response = self.client.post(
            "/api/orders/",
            data=json.dumps(
                {
                    "paymentMethod": "cod",
                    "name": "Afia Rahman",
                    "phone": "01700000000",
                    "area": "inside",
                    "address": "Dhanmondi, Dhaka",
                    "items": [{"id": product.slug, "quantity": 2}],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get()
        self.assertEqual(order.subtotal, product.price * 2)
        self.assertEqual(order.delivery_fee, 70)
        self.assertEqual(order.total, product.price * 2 + 70)
        self.assertEqual(order.status, Order.STATUS_PENDING)
        self.assertEqual(order.items.count(), 1)

    def test_orders_api_rejects_incomplete_customer_details(self):
        product = Product.objects.get(slug="party-cards")

        response = self.client.post(
            "/api/orders/",
            data=json.dumps(
                {
                    "paymentMethod": "cod",
                    "name": "",
                    "phone": "123",
                    "area": "inside",
                    "address": "",
                    "items": [{"id": product.slug, "quantity": "many"}],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_customer_can_login_and_redeem_coupon_once(self):
        user = User.objects.create_user(username="afia@example.com", email="afia@example.com", password="secret12345")
        coupon = Coupon.objects.get(code="TEEN10")
        product = Product.objects.get(slug="party-cards")

        login_response = self.client.post(
            "/api/auth/login/",
            data=json.dumps({"email": user.email, "password": "secret12345"}),
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)

        order_payload = {
            "paymentMethod": "cod",
            "name": "Afia Rahman",
            "phone": "01700000000",
            "area": "inside",
            "address": "Dhanmondi, Dhaka",
            "couponCode": coupon.code,
            "items": [{"id": product.slug, "quantity": 1}],
        }
        response = self.client.post("/api/orders/", data=json.dumps(order_payload), content_type="application/json")

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(user=user)
        self.assertEqual(order.discount, 28)
        self.assertEqual(order.total, 322)
        self.assertEqual(CouponRedemption.objects.filter(coupon=coupon, user=user).count(), 1)

        second_response = self.client.post("/api/orders/", data=json.dumps(order_payload), content_type="application/json")
        self.assertEqual(second_response.status_code, 400)

    def test_staff_dashboard_can_confirm_pending_order(self):
        staff = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="secret12345",
            is_staff=True,
        )
        product = Product.objects.get(slug="party-cards")
        order = Order.objects.create(
            customer_name="Afia Rahman",
            phone="01700000000",
            area=Order.AREA_INSIDE,
            address="Dhanmondi, Dhaka",
            payment_method=Order.PAYMENT_COD,
            subtotal=product.price,
            delivery_fee=70,
            total=product.price + 70,
        )

        self.client.force_login(staff)
        response = self.client.post(
            f"/api/dashboard/orders/{order.pk}/status/",
            data=json.dumps({"status": Order.STATUS_CONFIRMED}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_CONFIRMED)
        self.assertEqual(order.confirmed_by, staff)

        invalid_response = self.client.post(
            f"/api/dashboard/orders/{order.pk}/status/",
            data=json.dumps({"status": Order.STATUS_PENDING}),
            content_type="application/json",
        )
        self.assertEqual(invalid_response.status_code, 400)

        delivered_response = self.client.post(
            f"/api/dashboard/orders/{order.pk}/status/",
            data=json.dumps({"status": Order.STATUS_RECEIVED}),
            content_type="application/json",
        )
        self.assertEqual(delivered_response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.get_status_display(), "Delivered")
