const dashboardMessage = document.querySelector("#dashboardMessage");
const adminOrders = document.querySelector("#adminOrders");
const recentOrders = document.querySelector("#recentOrders");
const productRows = document.querySelector("#productRows");
const customerRows = document.querySelector("#customerRows");
const couponRows = document.querySelector("#couponRows");
const productDialog = document.querySelector("#productDialog");
const couponDialog = document.querySelector("#couponDialog");
const productForm = document.querySelector("#productForm");
const couponForm = document.querySelector("#couponForm");

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" };
const VIEW_META = {
  overview: ["Store workspace", "Overview"],
  orders: ["Fulfilment", "Orders"],
  products: ["Catalog", "Products"],
  customers: ["Accounts", "Customers"],
  coupons: ["Promotions", "Coupons"],
};

let activeStatus = "";
let products = [];
let customers = [];
let coupons = [];
let toastTimer;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => HTML_ESCAPES[character]);
}

function csrfToken() {
  return document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith("csrftoken="))
    ?.split("=")[1] || "";
}

function jsonHeaders() {
  return { "Content-Type": "application/json", "X-CSRFToken": csrfToken() };
}

function formatTk(value) {
  return `Tk ${Number(value || 0).toLocaleString("en-BD")}`;
}

function formatDate(value, includeTime = false) {
  const options = includeTime ? { dateStyle: "medium", timeStyle: "short" } : { dateStyle: "medium" };
  return new Intl.DateTimeFormat("en-BD", options).format(new Date(value));
}

function showMessage(message) {
  clearTimeout(toastTimer);
  dashboardMessage.textContent = message || "";
  if (message) toastTimer = setTimeout(() => { dashboardMessage.textContent = ""; }, 4500);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, { credentials: "same-origin", ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}

function emptyRow(columns, message) {
  return `<tr><td colspan="${columns}"><div class="admin-empty">${escapeHtml(message)}</div></td></tr>`;
}

function setView(view) {
  if (!VIEW_META[view]) view = "overview";
  document.querySelectorAll("[data-panel]").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === view));
  document.querySelectorAll(".admin-nav [data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  document.querySelector("#viewEyebrow").textContent = VIEW_META[view][0];
  document.querySelector("#viewTitle").textContent = VIEW_META[view][1];
  document.body.classList.remove("sidebar-open");
  history.replaceState(null, "", `#${view}`);

  if (view === "overview") loadOverview();
  if (view === "orders") loadOrders();
  if (view === "products") loadProducts();
  if (view === "customers") loadCustomers();
  if (view === "coupons") loadCoupons();
}

function statusBadge(status, label) {
  return `<span class="status-pill status-${escapeHtml(status)}">${escapeHtml(label)}</span>`;
}

function renderRecentOrders(orders) {
  recentOrders.innerHTML = orders.length
    ? orders.map((order) => `
        <div class="recent-order-row">
          <div class="recent-order-customer"><strong>#${order.id} ${escapeHtml(order.customerName)}</strong><small>${formatDate(order.createdAt, true)}</small></div>
          <span>${escapeHtml(order.items.map((item) => `${item.quantity} x ${item.name}`).join(", "))}</span>
          <strong>${formatTk(order.total)}</strong>
          ${statusBadge(order.status, order.statusLabel)}
        </div>
      `).join("")
    : `<div class="admin-empty">No orders yet.</div>`;
}

async function loadOverview() {
  try {
    const data = await fetchJson("/api/dashboard/overview/");
    document.querySelector("#overviewValue").textContent = formatTk(data.stats.orderValue);
    document.querySelector("#overviewOrders").textContent = data.stats.orders;
    document.querySelector("#overviewToday").textContent = `${data.stats.today} today`;
    document.querySelector("#overviewPending").textContent = data.stats.pending;
    document.querySelector("#overviewProducts").textContent = data.stats.products;
    document.querySelector("#overviewCustomers").textContent = `${data.stats.customers} customers`;
    document.querySelector("#navPending").textContent = data.stats.pending;
    renderRecentOrders(data.recentOrders);
  } catch (error) {
    showMessage(error.message);
  }
}

function renderOrderActions(order) {
  const actions = {
    confirmed: ["Accept order", "inline-button"],
    received: ["Mark delivered", "inline-button ghost"],
    cancelled: ["Cancel order", "inline-button danger"],
  };
  const buttons = order.allowedStatuses.map((status) => {
    const [label, className] = actions[status];
    return `<button class="${className}" type="button" data-order-status="${status}" data-order-id="${order.id}">${label}</button>`;
  });
  return buttons.length ? buttons.join("") : `<span class="order-complete">No more action needed</span>`;
}

function renderOrders(orders) {
  adminOrders.innerHTML = orders.length
    ? orders.map((order) => `
        <article class="admin-order-card">
          <div class="admin-order-top">
            <div>
              <span class="message-label">${order.status === "pending" ? "Needs review" : "Order update"}</span>
              <h3>#${order.id} ${escapeHtml(order.customerName)}</h3>
              <p>${escapeHtml(order.phone)} | ${escapeHtml(order.email)} | ${formatDate(order.createdAt, true)}</p>
            </div>
            ${statusBadge(order.status, order.statusLabel)}
          </div>
          <div class="admin-order-body">
            <div><strong>Items</strong>${order.items.map((item) => `<span>${item.quantity} x ${escapeHtml(item.name)}</span>`).join("")}</div>
            <div><strong>Delivery</strong><span>${escapeHtml(order.address)}</span><span>${order.area === "inside" ? "Inside Dhaka" : "Outside Dhaka"}</span></div>
            <div><strong>Total</strong><span>${formatTk(order.total)}</span><span>${order.paymentMethod === "cod" ? "Cash on delivery" : "bKash"}${order.coupon ? ` | ${escapeHtml(order.coupon)}` : ""}</span></div>
          </div>
          <div class="admin-actions">${renderOrderActions(order)}</div>
        </article>
      `).join("")
    : `<div class="admin-empty">No orders match this filter.</div>`;
}

function renderOrderStats(stats) {
  const total = stats.pending + stats.confirmed + stats.received + stats.cancelled;
  document.querySelector("#statAll").textContent = total;
  document.querySelector("#statPending").textContent = stats.pending;
  document.querySelector("#statConfirmed").textContent = stats.confirmed;
  document.querySelector("#statReceived").textContent = stats.received;
  document.querySelector("#statCancelled").textContent = stats.cancelled;
  document.querySelector("#navPending").textContent = stats.pending;
}

async function loadOrders() {
  try {
    const query = activeStatus ? `?status=${activeStatus}` : "";
    const data = await fetchJson(`/api/dashboard/orders/${query}`);
    renderOrderStats(data.stats);
    renderOrders(data.orders);
  } catch (error) {
    showMessage(error.message);
  }
}

async function updateOrderStatus(orderId, status, button) {
  button.disabled = true;
  try {
    const data = await fetchJson(`/api/dashboard/orders/${orderId}/status/`, {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify({ status }),
    });
    await loadOrders();
    showMessage(`Order #${data.order.id} is now ${data.order.statusLabel}.`);
  } catch (error) {
    button.disabled = false;
    showMessage(error.message);
  }
}

function productRow(product) {
  const image = product.image || "/assets/trendy-stylishness-logo-transparent.png";
  return `
    <tr>
      <td><div class="table-product"><img src="${escapeHtml(image)}" alt=""><span><strong>${escapeHtml(product.name)}</strong><small>${escapeHtml(product.tag || product.id)}</small></span></div></td>
      <td>${escapeHtml(product.category)}</td>
      <td><strong>${formatTk(product.price)}</strong></td>
      <td><span class="table-status ${product.isActive ? "active" : "hidden"}">${product.isActive ? "Visible" : "Hidden"}</span></td>
      <td>${product.sortOrder}</td>
      <td><div class="toolbar-actions"><button class="table-action" type="button" data-edit-product="${product.databaseId}">Edit</button><button class="table-action" type="button" data-toggle-product="${product.databaseId}">${product.isActive ? "Hide" : "Show"}</button></div></td>
    </tr>`;
}

function renderProducts() {
  const query = document.querySelector("#productSearch").value.trim().toLowerCase();
  const visible = products.filter((product) => `${product.name} ${product.tag} ${product.category}`.toLowerCase().includes(query));
  productRows.innerHTML = visible.length ? visible.map(productRow).join("") : emptyRow(6, "No products found.");
}

async function loadProducts() {
  try {
    const data = await fetchJson("/api/dashboard/products/");
    products = data.products;
    renderProducts();
  } catch (error) {
    showMessage(error.message);
  }
}

function openProductDialog(product = null) {
  productForm.reset();
  productForm.elements.productId.value = product?.databaseId || "";
  productForm.elements.name.value = product?.name || "";
  productForm.elements.category.value = product?.category || "cards";
  productForm.elements.price.value = product?.price || "";
  productForm.elements.tag.value = product?.tag || "";
  productForm.elements.sortOrder.value = product?.sortOrder || 0;
  productForm.elements.staticImagePath.value = product?.staticImagePath || "";
  productForm.elements.isActive.checked = product ? product.isActive : true;
  productForm.elements.removeImage.checked = false;
  document.querySelector("#productDialogTitle").textContent = product ? "Edit product" : "Add product";
  document.querySelector("#deleteProductButton").hidden = !product;
  document.querySelector("#removeImageLabel").hidden = !product?.hasUploadedImage;
  document.querySelector("#productFormMessage").textContent = "";
  productDialog.showModal();
}

function productFormData(product, changes = {}) {
  const formData = new FormData();
  formData.set("name", changes.name ?? product.name);
  formData.set("category", changes.category ?? product.category);
  formData.set("price", changes.price ?? product.price);
  formData.set("tag", changes.tag ?? product.tag);
  formData.set("sortOrder", changes.sortOrder ?? product.sortOrder);
  formData.set("staticImagePath", changes.staticImagePath ?? product.staticImagePath);
  formData.set("isActive", String(changes.isActive ?? product.isActive));
  return formData;
}

async function saveProductForm(event) {
  event.preventDefault();
  const submitButton = productForm.querySelector("button[type='submit']");
  submitButton.disabled = true;
  const productId = productForm.elements.productId.value;
  const formData = new FormData(productForm);
  formData.set("isActive", String(productForm.elements.isActive.checked));
  formData.set("removeImage", String(productForm.elements.removeImage.checked));
  try {
    const url = productId ? `/api/dashboard/products/${productId}/update/` : "/api/dashboard/products/create/";
    const data = await fetchJson(url, { method: "POST", headers: { "X-CSRFToken": csrfToken() }, body: formData });
    productDialog.close();
    await loadProducts();
    await loadOverview();
    showMessage(`${data.product.name} saved.`);
  } catch (error) {
    document.querySelector("#productFormMessage").textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
}

async function toggleProduct(productId) {
  const product = products.find((item) => item.databaseId === Number(productId));
  if (!product) return;
  try {
    await fetchJson(`/api/dashboard/products/${product.databaseId}/update/`, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken() },
      body: productFormData(product, { isActive: !product.isActive }),
    });
    await loadProducts();
    showMessage(`${product.name} is now ${product.isActive ? "hidden" : "visible"}.`);
  } catch (error) {
    showMessage(error.message);
  }
}

async function deleteCurrentProduct() {
  const productId = productForm.elements.productId.value;
  const product = products.find((item) => item.databaseId === Number(productId));
  if (!product || !window.confirm(`Delete ${product.name}?`)) return;
  try {
    await fetchJson(`/api/dashboard/products/${productId}/delete/`, { method: "POST", headers: jsonHeaders(), body: "{}" });
    productDialog.close();
    await loadProducts();
    await loadOverview();
    showMessage(`${product.name} deleted.`);
  } catch (error) {
    document.querySelector("#productFormMessage").textContent = error.message;
  }
}

function verificationChip(verified, label) {
  return `<span class="verify-chip ${verified ? "verified" : "unverified"}">${escapeHtml(label)} ${verified ? "yes" : "no"}</span>`;
}

function customerRow(customer) {
  const initial = (customer.name || customer.email || "C").charAt(0).toUpperCase();
  return `
    <tr>
      <td><div class="table-person"><span class="table-avatar">${escapeHtml(initial)}</span><span><strong>${escapeHtml(customer.name)}</strong><small>${escapeHtml(customer.email)}</small></span></div></td>
      <td>${escapeHtml(customer.phone || "Not saved")}</td>
      <td><div class="verification-stack">${verificationChip(customer.phoneVerified, "Phone")}${verificationChip(customer.emailVerified, "Email")}</div></td>
      <td>${customer.orders}</td>
      <td><strong>${formatTk(customer.orderTotal)}</strong></td>
      <td>${formatDate(customer.joinedAt)}</td>
    </tr>`;
}

function renderCustomers() {
  const query = document.querySelector("#customerSearch").value.trim().toLowerCase();
  const visible = customers.filter((customer) => `${customer.name} ${customer.email} ${customer.phone}`.toLowerCase().includes(query));
  customerRows.innerHTML = visible.length ? visible.map(customerRow).join("") : emptyRow(6, "No customers found.");
}

async function loadCustomers() {
  try {
    const data = await fetchJson("/api/dashboard/customers/");
    customers = data.customers;
    renderCustomers();
  } catch (error) {
    showMessage(error.message);
  }
}

function couponRow(coupon) {
  const discount = coupon.discountType === "percent" ? `${coupon.value}%` : formatTk(coupon.value);
  return `
    <tr>
      <td><strong>${escapeHtml(coupon.code)}</strong></td>
      <td>${discount} <small>${escapeHtml(coupon.discountLabel)}</small></td>
      <td>${coupon.redemptions}</td>
      <td>${coupon.singleUse ? "Once per customer" : "Reusable"}</td>
      <td><span class="table-status ${coupon.isActive ? "active" : "hidden"}">${coupon.isActive ? "Active" : "Inactive"}</span></td>
      <td><div class="toolbar-actions"><button class="table-action" type="button" data-edit-coupon="${coupon.id}">Edit</button><button class="table-action" type="button" data-toggle-coupon="${coupon.id}">${coupon.isActive ? "Disable" : "Enable"}</button></div></td>
    </tr>`;
}

function renderCoupons() {
  couponRows.innerHTML = coupons.length ? coupons.map(couponRow).join("") : emptyRow(6, "No coupons yet.");
}

async function loadCoupons() {
  try {
    const data = await fetchJson("/api/dashboard/coupons/");
    coupons = data.coupons;
    renderCoupons();
  } catch (error) {
    showMessage(error.message);
  }
}

function openCouponDialog(coupon = null) {
  couponForm.reset();
  couponForm.elements.couponId.value = coupon?.id || "";
  couponForm.elements.code.value = coupon?.code || "";
  couponForm.elements.discountType.value = coupon?.discountType || "percent";
  couponForm.elements.value.value = coupon?.value || "";
  couponForm.elements.isActive.checked = coupon ? coupon.isActive : true;
  couponForm.elements.singleUse.checked = coupon ? coupon.singleUse : true;
  document.querySelector("#couponDialogTitle").textContent = coupon ? "Edit coupon" : "Add coupon";
  document.querySelector("#couponFormMessage").textContent = "";
  couponDialog.showModal();
}

function couponPayload(coupon = null, changes = {}) {
  return {
    code: changes.code ?? coupon?.code ?? couponForm.elements.code.value,
    discountType: changes.discountType ?? coupon?.discountType ?? couponForm.elements.discountType.value,
    value: changes.value ?? coupon?.value ?? Number(couponForm.elements.value.value),
    isActive: changes.isActive ?? coupon?.isActive ?? couponForm.elements.isActive.checked,
    singleUse: changes.singleUse ?? coupon?.singleUse ?? couponForm.elements.singleUse.checked,
  };
}

async function saveCouponForm(event) {
  event.preventDefault();
  const submitButton = couponForm.querySelector("button[type='submit']");
  submitButton.disabled = true;
  const couponId = couponForm.elements.couponId.value;
  try {
    const url = couponId ? `/api/dashboard/coupons/${couponId}/update/` : "/api/dashboard/coupons/create/";
    const data = await fetchJson(url, { method: "POST", headers: jsonHeaders(), body: JSON.stringify(couponPayload()) });
    couponDialog.close();
    await loadCoupons();
    showMessage(`${data.coupon.code} saved.`);
  } catch (error) {
    document.querySelector("#couponFormMessage").textContent = error.message;
  } finally {
    submitButton.disabled = false;
  }
}

async function toggleCoupon(couponId) {
  const coupon = coupons.find((item) => item.id === Number(couponId));
  if (!coupon) return;
  try {
    await fetchJson(`/api/dashboard/coupons/${coupon.id}/update/`, {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify(couponPayload(coupon, { isActive: !coupon.isActive })),
    });
    await loadCoupons();
    showMessage(`${coupon.code} is now ${coupon.isActive ? "inactive" : "active"}.`);
  } catch (error) {
    showMessage(error.message);
  }
}

document.addEventListener("click", (event) => {
  const viewButton = event.target.closest("[data-view]");
  const statusButton = event.target.closest("[data-status]");
  const orderAction = event.target.closest("[data-order-status]");
  const editProduct = event.target.closest("[data-edit-product]");
  const toggleProductButton = event.target.closest("[data-toggle-product]");
  const editCoupon = event.target.closest("[data-edit-coupon]");
  const toggleCouponButton = event.target.closest("[data-toggle-coupon]");
  const closeDialog = event.target.closest("[data-close-dialog]");

  if (viewButton) setView(viewButton.dataset.view);
  if (statusButton) {
    activeStatus = statusButton.dataset.status;
    document.querySelectorAll("[data-status]").forEach((button) => button.classList.remove("active"));
    statusButton.classList.add("active");
    loadOrders();
  }
  if (orderAction) updateOrderStatus(orderAction.dataset.orderId, orderAction.dataset.orderStatus, orderAction);
  if (event.target.closest("[data-add-product]")) openProductDialog();
  if (editProduct) openProductDialog(products.find((product) => product.databaseId === Number(editProduct.dataset.editProduct)));
  if (toggleProductButton) toggleProduct(toggleProductButton.dataset.toggleProduct);
  if (event.target.closest("[data-add-coupon]")) openCouponDialog();
  if (editCoupon) openCouponDialog(coupons.find((coupon) => coupon.id === Number(editCoupon.dataset.editCoupon)));
  if (toggleCouponButton) toggleCoupon(toggleCouponButton.dataset.toggleCoupon);
  if (closeDialog) document.querySelector(`#${closeDialog.dataset.closeDialog}`).close();
  if (event.target.closest("[data-toggle-sidebar]")) document.body.classList.toggle("sidebar-open");
  if (event.target.closest("[data-admin-logout]")) {
    fetchJson("/api/auth/logout/", { method: "POST", headers: jsonHeaders(), body: "{}" })
      .then(() => { window.location.href = "/admin/login/?next=/dashboard/"; })
      .catch((error) => showMessage(error.message));
  }
});

document.querySelector("#productSearch").addEventListener("input", renderProducts);
document.querySelector("#customerSearch").addEventListener("input", renderCustomers);
document.querySelector("#deleteProductButton").addEventListener("click", deleteCurrentProduct);
productForm.addEventListener("submit", saveProductForm);
couponForm.addEventListener("submit", saveCouponForm);

setView(window.location.hash.slice(1) || "overview");
