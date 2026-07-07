const products = [
  {
    id: "party-cards",
    name: "Color Clash Party Cards",
    category: "cards",
    price: 280,
    image: "assets/cards-party-pack.png",
    tag: "Best for hangouts",
  },
  {
    id: "mini-charms",
    name: "Phone Charm Mini Set",
    category: "accessories",
    price: 190,
    image: "assets/accessory-bundle.png",
    tag: "Cute daily carry",
  },
  {
    id: "sticker-stationery",
    name: "Sticker Desk Gift Kit",
    category: "stationery",
    price: 340,
    image: "assets/stationery-gift-set.png",
    tag: "Gift ready",
  },
  {
    id: "friendship-pack",
    name: "Friendship Fancy Bundle",
    category: "accessories",
    price: 450,
    image: "assets/accessory-bundle.png",
    tag: "3 item combo",
  },
];

const cart = new Map();
const productGrid = document.querySelector("#productGrid");
const cartDrawer = document.querySelector("#cartDrawer");
const cartItems = document.querySelector("#cartItems");
const cartCount = document.querySelector("#cartCount");
const cartTotal = document.querySelector("#cartTotal");
const deliveryArea = document.querySelector("#deliveryArea");
const deliveryFee = document.querySelector("#deliveryFee");
const checkoutForm = document.querySelector("#checkoutForm");
const checkoutMessage = document.querySelector("#checkoutMessage");

function formatTk(value) {
  return `Tk ${value.toLocaleString("en-BD")}`;
}

function renderProducts(filter = "all") {
  const visibleProducts = filter === "all" ? products : products.filter((product) => product.category === filter);

  productGrid.innerHTML = visibleProducts
    .map(
      (product) => `
        <article class="product-card">
          <img src="${product.image}" alt="${product.name}">
          <div class="product-info">
            <div>
              <h3>${product.name}</h3>
              <div class="product-meta">
                <span>${product.tag}</span>
                <span class="price">${formatTk(product.price)}</span>
              </div>
            </div>
            <button class="add-button" type="button" data-add="${product.id}">Add to cart</button>
          </div>
        </article>
      `
    )
    .join("");
}

function getCartRows() {
  return [...cart.entries()].map(([id, quantity]) => {
    const product = products.find((item) => item.id === id);
    return { ...product, quantity };
  });
}

function updateCart() {
  const rows = getCartRows();
  const totalQty = rows.reduce((sum, item) => sum + item.quantity, 0);
  const total = rows.reduce((sum, item) => sum + item.price * item.quantity, 0);

  cartCount.textContent = totalQty;
  cartTotal.textContent = formatTk(total);

  cartItems.innerHTML = rows.length
    ? rows
        .map(
          (item) => `
            <div class="cart-item">
              <img src="${item.image}" alt="">
              <div>
                <strong>${item.name}</strong>
                <span>${item.quantity} x ${formatTk(item.price)}</span>
              </div>
              <button class="qty-button" type="button" data-remove="${item.id}" aria-label="Remove one ${item.name}">-</button>
            </div>
          `
        )
        .join("")
    : `<p class="form-note">Your cart is empty. Add a few tiny favorites first.</p>`;
}

function addToCart(id, quantity = 1) {
  cart.set(id, (cart.get(id) || 0) + quantity);
  updateCart();
}

function removeFromCart(id) {
  const nextQty = (cart.get(id) || 0) - 1;
  if (nextQty > 0) {
    cart.set(id, nextQty);
  } else {
    cart.delete(id);
  }
  updateCart();
}

function setCartOpen(open) {
  cartDrawer.classList.toggle("open", open);
  cartDrawer.setAttribute("aria-hidden", String(!open));
}

document.addEventListener("click", (event) => {
  const addButton = event.target.closest("[data-add]");
  const removeButton = event.target.closest("[data-remove]");
  const filterButton = event.target.closest("[data-filter]");

  if (addButton) {
    addToCart(addButton.dataset.add);
    setCartOpen(true);
  }

  if (removeButton) {
    removeFromCart(removeButton.dataset.remove);
  }

  if (filterButton) {
    document.querySelectorAll("[data-filter]").forEach((button) => button.classList.remove("active"));
    filterButton.classList.add("active");
    renderProducts(filterButton.dataset.filter);
  }

  if (event.target.closest("[data-open-cart]")) {
    setCartOpen(true);
  }

  if (event.target.closest("[data-close-cart]")) {
    setCartOpen(false);
  }

  if (event.target.closest("[data-bundle]")) {
    addToCart("party-cards");
    addToCart("mini-charms");
    addToCart("sticker-stationery");
    setCartOpen(true);
  }
});

deliveryArea.addEventListener("change", () => {
  deliveryFee.textContent = deliveryArea.value === "inside" ? "Tk 70" : "Tk 130";
});

checkoutForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const subtotal = getCartRows().reduce((sum, item) => sum + item.price * item.quantity, 0);
  const delivery = deliveryArea.value === "inside" ? 70 : 130;
  const payable = subtotal + delivery;

  checkoutMessage.textContent =
    payable > delivery
      ? `Demo only: next step would call /api/bkash/create-payment for ${formatTk(payable)} and /api/steadfast/order after payment success.`
      : "Add items to cart before starting bKash checkout.";
});

renderProducts();
updateCart();
