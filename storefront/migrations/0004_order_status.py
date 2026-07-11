from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("storefront", "0003_seed_coupon"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("confirmed", "Confirmed"),
                    ("received", "Received"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="status_note",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="order",
            name="confirmed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="confirmed_orders",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
