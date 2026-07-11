# Trendy Stylishness

A Django ecommerce storefront for small teen-focused items such as party cards,
phone charms, fancy accessories, stickers, stationery, and gift bundles.

The current visual direction blends a colorful graduation-pop hero with premium
streetwear styling: floating shop items, dark accent panels, polished controls,
and red, blue, chrome, cream, and acid-green accents.

## Files

- `index.html` - storefront markup
- `styles.css` - responsive visual design
- `script.js` - product filtering, cart, customer accounts, checkout, and order tracking
- `dashboard.html`, `dashboard.js` - staff order dashboard
- `assets/` - generated product and hero images
- `manage.py`, `trendy_backend/`, `storefront/` - Django backend, admin, API, and SQLite models

## Run Locally

For the database-backed Django version:

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Then visit:

```text
Storefront: http://127.0.0.1:8000/
Admin:      http://127.0.0.1:8000/admin/
```

Use the admin Product section to add, edit, deactivate, or delete products. Products
can use an uploaded image or a static fallback path such as
`assets/cards-party-pack.png`.

The staff dashboard also has direct shortcuts for products, customers, and coupons.
Use `Visible in store` to hide a product without deleting its order history.

Customers can create accounts from the storefront. Signed-in checkout orders are
linked to the customer account, and admins can view order history, customer phone
and address data, coupons, and coupon redemptions in Django admin.

A starter coupon `TEEN10` is seeded for testing. It gives a 10% discount and can
be used once per customer account.

Orders follow one simple path: `Pending` -> `Confirmed` -> `Delivered`. Staff can
also cancel a pending or confirmed order. Customers see the current status and a
plain-language explanation in their account order history.

The static GitHub Pages version can still open `index.html` directly. It will try
the Django API first and fall back to the original demo products if no backend is
available.

## API Integration Notes

Current endpoints:

- `GET /api/products/` - returns active products from SQLite.
- `POST /api/orders/` - saves a checkout order and line items.
- `POST /api/auth/register/` - creates a customer login.
- `POST /api/auth/login/` - signs in an existing customer.
- `POST /api/auth/logout/` - signs out the current customer.
- `GET /api/auth/me/` - returns the signed-in customer and recent orders.
- `GET /api/dashboard/orders/` - staff-only order dashboard feed.
- `POST /api/dashboard/orders/<id>/status/` - staff-only order status update.

The current bKash choice records the customer's payment preference; it does not
charge the customer automatically. For production, add bKash payment
creation/execution and courier calls inside the Django backend. Keep credentials
on the server, never in browser JavaScript.
