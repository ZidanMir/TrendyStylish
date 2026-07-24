const fallbackProducts = [
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

let products = [...fallbackProducts];
const API_BASE = window.TRENDY_API_BASE || "";
const cart = new Map();
const productGrid = document.querySelector("#productGrid");
const cartDrawer = document.querySelector("#cartDrawer");
const cartItems = document.querySelector("#cartItems");
const cartCount = document.querySelector("#cartCount");
const cartTotal = document.querySelector("#cartTotal");
const deliveryArea = document.querySelector("#deliveryArea");
const deliveryFee = document.querySelector("#deliveryFee");
const checkoutSubtotal = document.querySelector("#checkoutSubtotal");
const checkoutEstimate = document.querySelector("#checkoutEstimate");
const checkoutForm = document.querySelector("#checkoutForm");
const checkoutButton = document.querySelector("#checkoutButton");
const checkoutMessage = document.querySelector("#checkoutMessage");
const paymentMethods = document.querySelectorAll("input[name='paymentMethod']");
const accountModal = document.querySelector("#accountModal");
const accountLabel = document.querySelector("#accountLabel");
const accountSummary = document.querySelector("#accountSummary");
const checkoutAccountText = document.querySelector("#checkoutAccountText");
const orderEmailNote = document.querySelector("#orderEmailNote");
const registeredPhoneText = document.querySelector("#registeredPhoneText");
const deliveryPhoneInput = document.querySelector("#deliveryPhoneInput");
const deliveryPhoneModes = document.querySelectorAll("input[name='deliveryPhoneMode']");
const authForm = document.querySelector("#authForm");
const authTabs = document.querySelector(".auth-tabs");
const authButton = document.querySelector("#authButton");
const authMessage = document.querySelector("#authMessage");
const phoneVerifyStatus = document.querySelector("#phoneVerifyStatus");
const phoneVerifyMessage = document.querySelector("#phoneVerifyMessage");
const emailVerifyStatus = document.querySelector("#emailVerifyStatus");
const emailVerifyMessage = document.querySelector("#emailVerifyMessage");
const emailCodeRow = document.querySelector("#emailCodeRow");
const emailCode = document.querySelector("#emailCode");
const customerPanel = document.querySelector("#customerPanel");
const customerName = document.querySelector("#customerName");
const customerEmail = document.querySelector("#customerEmail");
const orderHistory = document.querySelector("#orderHistory");
let authMode = "login";
let currentCustomer = null;
let customerOrders = [];
let verifiedSignupPhone = "";

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => HTML_ESCAPES[character]);
}

function csrfHeaders() {
  const token = document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith("csrftoken="))
    ?.split("=")[1];
  return { "Content-Type": "application/json", "X-CSRFToken": token || "" };
}

function formatTk(value) {
  return `Tk ${value.toLocaleString("en-BD")}`;
}

function formatDate(value) {
  return new Intl.DateTimeFormat("en-BD", { dateStyle: "medium" }).format(new Date(value));
}

function renderProducts(filter = "all") {
  const visibleProducts = filter === "all" ? products : products.filter((product) => product.category === filter);

  if (!visibleProducts.length) {
    productGrid.innerHTML = `<p class="form-note">No products are available in this category yet.</p>`;
    return;
  }

  productGrid.innerHTML = visibleProducts
    .map(
      (product) => `
        <article class="product-card">
          <img src="${escapeHtml(product.image)}" alt="${escapeHtml(product.name)}">
          <div class="product-info">
            <div>
              <h3>${escapeHtml(product.name)}</h3>
              <div class="product-meta">
                <span>${escapeHtml(product.tag)}</span>
                <span class="price">${formatTk(product.price)}</span>
              </div>
            </div>
              <button class="add-button" type="button" data-add="${escapeHtml(product.id)}">Add to cart</button>
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
  }).filter((item) => item.id);
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
              <img src="${escapeHtml(item.image)}" alt="">
              <div>
                <strong>${escapeHtml(item.name)}</strong>
                <span>${item.quantity} x ${formatTk(item.price)}</span>
              </div>
              <button class="qty-button" type="button" data-remove="${escapeHtml(item.id)}" aria-label="Remove one ${escapeHtml(item.name)}">-</button>
            </div>
          `
        )
        .join("")
    : `<p class="form-note">Your cart is empty. Add a few tiny favorites first.</p>`;

  updateCheckoutTotals();
}

function updateCheckoutTotals() {
  const subtotal = getCartRows().reduce((sum, item) => sum + item.price * item.quantity, 0);
  const fee = deliveryArea.value === "inside" ? 70 : 130;
  checkoutSubtotal.textContent = formatTk(subtotal);
  deliveryFee.textContent = formatTk(fee);
  checkoutEstimate.textContent = formatTk(subtotal + fee);
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

function setAccountOpen(open) {
  accountModal.classList.toggle("open", open);
  accountModal.setAttribute("aria-hidden", String(!open));
}

function setAuthMode(mode) {
  authMode = mode;
  document.querySelectorAll("[data-auth-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.authMode === mode);
  });
  document.querySelectorAll(".register-only").forEach((field) => {
    field.hidden = mode !== "register";
  });
  authButton.textContent = mode === "register" ? "Create account" : "Login";
  const passwordInput = authForm.elements.password;
  passwordInput.autocomplete = mode === "register" ? "new-password" : "current-password";
  passwordInput.minLength = mode === "register" ? 8 : 0;
  passwordInput.placeholder = mode === "register" ? "At least 8 characters" : "Your password";
  authForm.elements.name.required = mode === "register";
  authForm.elements.phone.required = mode === "register";
  syncAuthSubmitState();
  authMessage.textContent = "";
}

function syncAuthSubmitState() {
  authButton.disabled = authMode === "register" && !verifiedSignupPhone;
}

function resetPhoneVerification() {
  verifiedSignupPhone = "";
  phoneVerifyStatus.textContent = "Required";
  phoneVerifyStatus.classList.remove("verified");
  phoneVerifyMessage.textContent = "";
  syncAuthSubmitState();
}

async function sendPhoneVerificationCode() {
  const phone = authForm.elements.phone.value;
  const channel = authForm.querySelector("input[name='phoneChannel']:checked")?.value || "sms";
  phoneVerifyMessage.textContent = channel === "call" ? "Requesting phone call..." : "Sending text message...";
  try {
    const response = await fetch(`${API_BASE}/api/auth/phone/send/`, {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders(),
      body: JSON.stringify({ phone, channel }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not send verification code.");
    authForm.elements.phone.value = data.phone;
    if (data.debugCode) authForm.elements.phoneCode.value = data.debugCode;
    phoneVerifyMessage.textContent = data.debugCode
      ? `Local test code: ${data.debugCode}`
      : channel === "call" ? "Answer the call and enter the code." : "Code sent by text message.";
  } catch (error) {
    phoneVerifyMessage.textContent = error.message;
  }
}

async function checkPhoneVerificationCode() {
  phoneVerifyMessage.textContent = "Checking code...";
  try {
    const response = await fetch(`${API_BASE}/api/auth/phone/verify/`, {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders(),
      body: JSON.stringify({ phone: authForm.elements.phone.value, code: authForm.elements.phoneCode.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Phone verification failed.");
    verifiedSignupPhone = data.phone;
    authForm.elements.phone.value = data.phone;
    phoneVerifyStatus.textContent = "Verified";
    phoneVerifyStatus.classList.add("verified");
    phoneVerifyMessage.textContent = "Phone number verified. You can create your account.";
    syncAuthSubmitState();
  } catch (error) {
    resetPhoneVerification();
    phoneVerifyMessage.textContent = error.message;
  }
}

async function sendEmailVerificationCode() {
  emailVerifyMessage.textContent = "Sending verification email...";
  try {
    const response = await fetch(`${API_BASE}/api/auth/email/send/`, {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders(),
      body: "{}",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not send verification email.");
    emailCodeRow.hidden = false;
    if (data.debugCode) emailCode.value = data.debugCode;
    emailVerifyMessage.textContent = data.debugCode ? `Local test code: ${data.debugCode}` : data.message;
  } catch (error) {
    emailVerifyMessage.textContent = error.message;
  }
}

async function checkEmailVerificationCode() {
  emailVerifyMessage.textContent = "Checking code...";
  try {
    const response = await fetch(`${API_BASE}/api/auth/email/verify/`, {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders(),
      body: JSON.stringify({ code: emailCode.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Email verification failed.");
    currentCustomer = data.user;
    emailVerifyMessage.textContent = "Email verified.";
    renderCustomer();
  } catch (error) {
    emailVerifyMessage.textContent = error.message;
  }
}

function renderCustomer() {
  const signedIn = Boolean(currentCustomer);
  accountLabel.textContent = signedIn ? currentCustomer.name.split(" ")[0] : "Sign in";
  authTabs.hidden = signedIn;
  authForm.hidden = signedIn;
  customerPanel.hidden = !signedIn;

  checkoutAccountText.textContent = signedIn
    ? `Signed in as ${currentCustomer.name}. Orders and coupon use will be saved.`
    : "Sign in to save orders, track history, and redeem coupons.";
  accountSummary.querySelector(".inline-button").hidden = signedIn;

  if (!signedIn) {
    customerName.textContent = "";
    customerEmail.textContent = "";
    orderHistory.innerHTML = "";
    updateDeliveryContact();
    return;
  }

  customerName.textContent = currentCustomer.name;
  customerEmail.textContent = currentCustomer.email;
  emailVerifyStatus.textContent = currentCustomer.emailVerified ? "Verified" : "Optional";
  emailVerifyStatus.classList.toggle("verified", currentCustomer.emailVerified);
  customerPanel.querySelector("[data-send-email-code]").hidden = currentCustomer.emailVerified;
  if (currentCustomer.emailVerified) emailCodeRow.hidden = true;
  const nameInput = checkoutForm.elements.name;
  const addressInput = checkoutForm.elements.address;

  if (!nameInput.value) nameInput.value = currentCustomer.name || "";
  if (!addressInput.value) addressInput.value = currentCustomer.address || "";
  updateDeliveryContact();

  orderHistory.innerHTML = customerOrders.length
    ? customerOrders
        .map(
          (order) => `
            <article class="history-item">
              <div class="history-main">
                <strong>Order #${order.id}</strong>
                <span>${formatDate(order.createdAt)}${order.coupon ? ` | Coupon ${escapeHtml(order.coupon)}` : ""}</span>
                <small>${order.items.map((item) => `${item.quantity} x ${escapeHtml(item.name)}`).join(", ")}</small>
              </div>
              <div class="history-status">
                <strong>${formatTk(order.total)}</strong>
                <em class="mini-status status-${escapeHtml(order.status)}">${escapeHtml(order.statusLabel)}</em>
              </div>
              <p>${escapeHtml(order.statusHelp)}${order.statusNote ? ` ${escapeHtml(order.statusNote)}` : ""}</p>
            </article>
          `
        )
        .join("")
    : `<p class="form-note">No saved orders yet.</p>`;
}

function updateDeliveryContact() {
  const registeredMode = checkoutForm.querySelector("input[name='deliveryPhoneMode'][value='registered']");
  const customMode = checkoutForm.querySelector("input[name='deliveryPhoneMode'][value='custom']");
  const customPhone = checkoutForm.elements.deliveryPhone;
  const registeredPhone = currentCustomer?.phone || "";
  const canUseRegisteredPhone = Boolean(currentCustomer && registeredPhone);

  orderEmailNote.querySelector("span").textContent = currentCustomer
    ? `Confirmation and tracking updates will go to ${currentCustomer.email}.`
    : "Sign in to receive confirmation and tracking updates at your registered email.";
  registeredPhoneText.textContent = canUseRegisteredPhone
    ? `Registered: ${registeredPhone}`
    : "No registered number available";
  registeredMode.disabled = !canUseRegisteredPhone;

  if (!canUseRegisteredPhone && registeredMode.checked) customMode.checked = true;
  const useCustomPhone = customMode.checked;
  deliveryPhoneInput.hidden = !useCustomPhone;
  customPhone.required = useCustomPhone;
}

async function loadCustomer() {
  try {
    const response = await fetch(`${API_BASE}/api/auth/me/`, { credentials: "same-origin" });
    const data = await response.json();
    currentCustomer = data.user;
    customerOrders = data.orders || [];
  } catch (error) {
    currentCustomer = null;
    customerOrders = [];
  }
  renderCustomer();
}

async function submitAuth(event) {
  event.preventDefault();
  if (authMode === "register" && !verifiedSignupPhone) {
    authMessage.textContent = "Verify your phone number before creating the account.";
    return;
  }
  const formData = new FormData(authForm);
  const payload = {
    email: formData.get("email"),
    password: formData.get("password"),
    name: formData.get("name"),
    phone: formData.get("phone"),
    address: formData.get("address"),
  };

  authButton.disabled = true;
  authMessage.textContent = authMode === "register" ? "Creating account..." : "Signing in...";

  try {
    const response = await fetch(`${API_BASE}/api/auth/${authMode}/`, {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders(),
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Account request failed.");
    }

    currentCustomer = data.user;
    customerOrders = [];
    authForm.reset();
    verifiedSignupPhone = "";
    authMessage.textContent = "";
    renderCustomer();
  } catch (error) {
    authMessage.textContent = error.message;
  } finally {
    syncAuthSubmitState();
  }
}

async function logoutCustomer() {
  await fetch(`${API_BASE}/api/auth/logout/`, {
    method: "POST",
    credentials: "same-origin",
    headers: csrfHeaders(),
  });
  currentCustomer = null;
  customerOrders = [];
  renderCustomer();
}

document.addEventListener("click", (event) => {
  const addButton = event.target.closest("[data-add]");
  const removeButton = event.target.closest("[data-remove]");
  const filterButton = event.target.closest("[data-filter]");
  const authModeButton = event.target.closest("[data-auth-mode]");

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

  if (event.target.closest("[data-open-account]")) {
    setAccountOpen(true);
  }

  if (event.target.closest("[data-close-cart]")) {
    setCartOpen(false);
  }

  if (event.target.closest("[data-close-account]")) {
    setAccountOpen(false);
  }

  if (authModeButton) {
    setAuthMode(authModeButton.dataset.authMode);
  }

  if (event.target.closest("[data-send-phone-code]")) {
    sendPhoneVerificationCode();
  }

  if (event.target.closest("[data-verify-phone-code]")) {
    checkPhoneVerificationCode();
  }

  if (event.target.closest("[data-send-email-code]")) {
    sendEmailVerificationCode();
  }

  if (event.target.closest("[data-verify-email-code]")) {
    checkEmailVerificationCode();
  }

  if (event.target.closest("[data-logout]")) {
    logoutCustomer();
  }

  if (event.target.closest("[data-bundle]")) {
    products.slice(0, 3).forEach((product) => addToCart(product.id));
    setCartOpen(true);
  }
});

deliveryArea.addEventListener("change", () => {
  updateCheckoutTotals();
});

function getPaymentMethod() {
  return document.querySelector("input[name='paymentMethod']:checked")?.value || "bkash";
}

function updatePaymentMethod() {
  const isCod = getPaymentMethod() === "cod";
  checkoutButton.textContent = isCod ? "Place cash on delivery order" : "Place order with bKash";
  checkoutButton.classList.toggle("cod-mode", isCod);
}

paymentMethods.forEach((method) => {
  method.addEventListener("change", updatePaymentMethod);
});

deliveryPhoneModes.forEach((mode) => {
  mode.addEventListener("change", updateDeliveryContact);
});

authForm.addEventListener("submit", submitAuth);
authForm.elements.phone.addEventListener("input", resetPhoneVerification);

async function loadProducts() {
  try {
    const response = await fetch(`${API_BASE}/api/products/`);
    if (!response.ok) {
      throw new Error("Product API failed");
    }

    const data = await response.json();
    products = Array.isArray(data.products) ? data.products : [];
  } catch (error) {
    products = [...fallbackProducts];
  }

  renderProducts(document.querySelector("[data-filter].active")?.dataset.filter || "all");
  updateCart();
}

checkoutForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const rows = getCartRows();
  const subtotal = rows.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const paymentMethod = getPaymentMethod();

  if (!subtotal) {
    checkoutMessage.textContent = "Add items to cart before starting checkout.";
    return;
  }
  if (!currentCustomer) {
    checkoutMessage.textContent = "Sign in before placing an order so updates can reach your registered email.";
    accountModal.classList.add("open");
    return;
  }

  const formData = new FormData(checkoutForm);
  const payload = {
    paymentMethod,
    name: formData.get("name"),
    deliveryPhoneMode: formData.get("deliveryPhoneMode"),
    deliveryPhone: formData.get("deliveryPhone"),
    area: formData.get("area"),
    address: formData.get("address"),
    couponCode: formData.get("couponCode"),
    items: rows.map((item) => ({ id: item.id, quantity: item.quantity })),
  };

  checkoutButton.disabled = true;
  checkoutMessage.textContent = "Saving your order...";

  try {
    const response = await fetch(`${API_BASE}/api/orders/`, {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders(),
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not save order.");
    }

    checkoutMessage.textContent = `Order #${data.id} placed for ${formatTk(data.total)}. ${data.message}`;
    cart.clear();
    updateCart();
    checkoutForm.reset();
    updateDeliveryContact();
    updatePaymentMethod();
    updateCheckoutTotals();
    loadCustomer();
  } catch (error) {
    checkoutMessage.textContent = error.message;
  } finally {
    checkoutButton.disabled = false;
  }
});

setAuthMode("login");
loadProducts();
loadCustomer();
updateCart();
updatePaymentMethod();
