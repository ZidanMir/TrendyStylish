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

New customers verify their Bangladesh mobile number by SMS or voice code before
signup. Email verification is optional and remains available inside the customer
account. Signed-in checkout orders are linked to the customer account.

A starter coupon `TEEN10` is seeded for testing. It gives a 10% discount and can
be used once per customer account.

Orders follow one simple path: `Pending` -> `Confirmed` -> `Delivered`. Staff can
also cancel a pending or confirmed order. Customers see the current status and a
plain-language explanation in their account order history. Order placement and
every status change also send an email to the address saved on the order.

## Verification And Email

Local development uses safe console delivery. Verification codes are shown in the
browser and email bodies are printed in the Django server terminal.

For real SMS and phone calls, create a Twilio Verify Service and set:

```powershell
$env:PHONE_VERIFY_BACKEND="twilio"
$env:TWILIO_VERIFY_SERVICE_SID="VA..."
$env:TWILIO_ACCOUNT_SID="AC..."
$env:TWILIO_AUTH_TOKEN="..."
```

Twilio API key credentials can be used instead through `TWILIO_API_KEY` and
`TWILIO_API_SECRET`.

For real outbound email, configure an SMTP account:

```powershell
$env:EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend"
$env:EMAIL_HOST="smtp.example.com"
$env:EMAIL_PORT="587"
$env:EMAIL_HOST_USER="orders@example.com"
$env:EMAIL_HOST_PASSWORD="..."
$env:EMAIL_USE_TLS="true"
$env:DEFAULT_FROM_EMAIL="Trendy Stylishness <orders@example.com>"
```

Restart Django after changing environment variables. Never commit provider
credentials to Git.

The static GitHub Pages version can still open `index.html` directly. It will try
the Django API first and fall back to the original demo products if no backend is
available.

## API Integration Notes

Current endpoints:

- `GET /api/products/` - returns active products from SQLite.
- `POST /api/orders/` - saves a checkout order and line items.
- `POST /api/auth/register/` - creates a customer login.
- `POST /api/auth/phone/send/` - sends a signup code by SMS or call.
- `POST /api/auth/phone/verify/` - verifies the signup phone code.
- `POST /api/auth/login/` - signs in an existing customer.
- `POST /api/auth/logout/` - signs out the current customer.
- `GET /api/auth/me/` - returns the signed-in customer and recent orders.
- `POST /api/auth/email/send/` - sends the optional email verification code.
- `POST /api/auth/email/verify/` - verifies the signed-in customer's email.
- `GET /api/dashboard/orders/` - staff-only order dashboard feed.
- `POST /api/dashboard/orders/<id>/status/` - staff-only order status update.

The current bKash choice records the customer's payment preference; it does not
charge the customer automatically. For production, add bKash payment
creation/execution and courier calls inside the Django backend. Keep credentials
on the server, never in browser JavaScript.
