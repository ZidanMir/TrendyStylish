# Trendy Stylishness

A frontend-first ecommerce concept for small teen-focused items such as party cards,
phone charms, fancy accessories, stickers, stationery, and gift bundles.

## Files

- `index.html` - storefront markup
- `styles.css` - responsive visual design
- `script.js` - product filtering, cart drawer, delivery estimate, and checkout demo
- `assets/` - generated product and hero images

## Run Locally

Open `index.html` directly in a browser, or run a tiny static server:

```powershell
python -m http.server 4173 --bind 127.0.0.1
```

Then visit:

```text
http://127.0.0.1:4173/index.html
```

## API Integration Notes

The page currently keeps payment and delivery as frontend demo flows. For production,
add small backend endpoints such as:

- `POST /api/bkash/create-payment` - creates a bKash payment session.
- `POST /api/bkash/execute-payment` - verifies and finalizes payment after callback.
- `POST /api/steadfast/order` - creates a delivery order after successful payment.

Keep bKash and Steadfast credentials on the server, never in browser JavaScript.
