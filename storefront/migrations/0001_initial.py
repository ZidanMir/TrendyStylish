from django.db import migrations, models
import django.db.models.deletion


def seed_products(apps, schema_editor):
    Product = apps.get_model("storefront", "Product")
    Product.objects.bulk_create(
        [
            Product(
                slug="party-cards",
                name="Color Clash Party Cards",
                category="cards",
                price=280,
                static_image_path="assets/cards-party-pack.png",
                tag="Best for hangouts",
                sort_order=10,
            ),
            Product(
                slug="mini-charms",
                name="Phone Charm Mini Set",
                category="accessories",
                price=190,
                static_image_path="assets/accessory-bundle.png",
                tag="Cute daily carry",
                sort_order=20,
            ),
            Product(
                slug="sticker-stationery",
                name="Sticker Desk Gift Kit",
                category="stationery",
                price=340,
                static_image_path="assets/stationery-gift-set.png",
                tag="Gift ready",
                sort_order=30,
            ),
            Product(
                slug="friendship-pack",
                name="Friendship Fancy Bundle",
                category="accessories",
                price=450,
                static_image_path="assets/accessory-bundle.png",
                tag="3 item combo",
                sort_order=40,
            ),
        ]
    )


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("customer_name", models.CharField(max_length=120)),
                ("phone", models.CharField(max_length=24)),
                ("area", models.CharField(choices=[("inside", "Inside Dhaka"), ("outside", "Outside Dhaka")], max_length=16)),
                ("address", models.TextField()),
                ("payment_method", models.CharField(choices=[("bkash", "bKash"), ("cod", "Cash on delivery")], max_length=16)),
                ("subtotal", models.PositiveIntegerField(default=0)),
                ("delivery_fee", models.PositiveIntegerField(default=0)),
                ("total", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=120)),
                ("category", models.CharField(choices=[("cards", "Cards"), ("accessories", "Accessories"), ("stationery", "Stationery")], max_length=32)),
                ("price", models.PositiveIntegerField(help_text="Price in Bangladeshi taka")),
                ("tag", models.CharField(blank=True, max_length=80)),
                ("image", models.ImageField(blank=True, upload_to="products/")),
                ("static_image_path", models.CharField(blank=True, help_text="Fallback static path, for example assets/cards-party-pack.png", max_length=180)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("product_name", models.CharField(max_length=120)),
                ("unit_price", models.PositiveIntegerField()),
                ("quantity", models.PositiveIntegerField()),
                ("line_total", models.PositiveIntegerField()),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="storefront.order")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="storefront.product")),
            ],
        ),
        migrations.RunPython(seed_products, migrations.RunPython.noop),
    ]
