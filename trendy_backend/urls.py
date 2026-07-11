from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from django.views.static import serve

from storefront import views


urlpatterns = [
    path("", views.storefront, name="storefront"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("admin/", admin.site.urls),
    path("api/products/", views.products_api, name="products_api"),
    path("api/orders/", views.orders_api, name="orders_api"),
    path("api/auth/register/", views.register_api, name="register_api"),
    path("api/auth/login/", views.login_api, name="login_api"),
    path("api/auth/logout/", views.logout_api, name="logout_api"),
    path("api/auth/me/", views.me_api, name="me_api"),
    path("api/dashboard/orders/", views.dashboard_orders_api, name="dashboard_orders_api"),
    path("api/dashboard/orders/<int:order_id>/status/", views.dashboard_order_status_api, name="dashboard_order_status_api"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        re_path(
            r"^(?P<path>styles\.css|script\.js|dashboard\.js|assets/.+)$",
            serve,
            {"document_root": settings.BASE_DIR},
        )
    ]
