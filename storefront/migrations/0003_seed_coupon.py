from django.db import migrations


def seed_coupon(apps, schema_editor):
    Coupon = apps.get_model("storefront", "Coupon")
    Coupon.objects.get_or_create(
        code="TEEN10",
        defaults={
            "discount_type": "percent",
            "value": 10,
            "is_active": True,
            "single_use_per_customer": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("storefront", "0002_coupon_order_discount_order_user_order_coupon_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_coupon, migrations.RunPython.noop),
    ]
