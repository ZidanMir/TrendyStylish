const adminOrders = document.querySelector("#adminOrders");
const dashboardMessage = document.querySelector("#dashboardMessage");
const statAll = document.querySelector("#statAll");
const statPending = document.querySelector("#statPending");
const statConfirmed = document.querySelector("#statConfirmed");
const statReceived = document.querySelector("#statReceived");
const statCancelled = document.querySelector("#statCancelled");
let activeStatus = "";

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
  return new Intl.DateTimeFormat("en-BD", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function renderStats(stats) {
  statPending.textContent = stats.pending;
  statConfirmed.textContent = stats.confirmed;
  statReceived.textContent = stats.received;
  statCancelled.textContent = stats.cancelled;
  statAll.textContent = stats.pending + stats.confirmed + stats.received + stats.cancelled;
}

function renderActions(order) {
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
  if (!orders.length) {
    adminOrders.innerHTML = `<div class="admin-empty">No orders match this view.</div>`;
    return;
  }

  adminOrders.innerHTML = orders
    .map(
      (order) => `
        <article class="admin-order-card">
          <div class="admin-order-top">
            <div>
              <span class="message-label">${order.status === "pending" ? "Needs review" : "Order update"}</span>
              <h2>#${order.id} ${escapeHtml(order.customerName)}</h2>
              <p>${escapeHtml(order.phone)} | ${escapeHtml(order.email)} | ${order.area === "inside" ? "Inside Dhaka" : "Outside Dhaka"} | ${formatDate(order.createdAt)}</p>
            </div>
            <span class="status-pill status-${escapeHtml(order.status)}">${escapeHtml(order.statusLabel)}</span>
          </div>
          <div class="admin-order-body">
            <div>
              <strong>Items</strong>
              ${order.items.map((item) => `<span>${item.quantity} x ${escapeHtml(item.name)}</span>`).join("")}
            </div>
            <div>
              <strong>Delivery</strong>
              <span>${escapeHtml(order.address)}</span>
            </div>
            <div>
              <strong>Total</strong>
              <span>${formatTk(order.total)}</span>
              <span>${order.paymentMethod === "cod" ? "Cash on delivery" : "bKash"}${order.coupon ? ` | ${escapeHtml(order.coupon)}` : ""}</span>
            </div>
          </div>
          <div class="admin-actions">${renderActions(order)}</div>
        </article>
      `
    )
    .join("");
}

async function loadOrders() {
  try {
    const query = activeStatus ? `?status=${activeStatus}` : "";
    const response = await fetch(`/api/dashboard/orders/${query}`, { credentials: "same-origin" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load dashboard orders.");

    renderStats(data.stats);
    renderOrders(data.orders);
    dashboardMessage.textContent = data.stats.pending
      ? `${data.stats.pending} pending order${data.stats.pending === 1 ? "" : "s"} waiting for review.`
      : "No pending orders right now.";
  } catch (error) {
    dashboardMessage.textContent = error.message;
  }
}

async function updateOrderStatus(orderId, status, button) {
  button.disabled = true;
  dashboardMessage.textContent = "Updating order...";
  try {
    const response = await fetch(`/api/dashboard/orders/${orderId}/status/`, {
      method: "POST",
      credentials: "same-origin",
      headers: csrfHeaders(),
      body: JSON.stringify({ status }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not update order.");

    await loadOrders();
    dashboardMessage.textContent = `Order #${data.order.id} is now ${data.order.statusLabel}.`;
  } catch (error) {
    dashboardMessage.textContent = error.message;
    button.disabled = false;
  }
}

document.addEventListener("click", (event) => {
  const filterButton = event.target.closest("[data-status]");
  const actionButton = event.target.closest("[data-order-status]");

  if (filterButton) {
    activeStatus = filterButton.dataset.status;
    document.querySelectorAll("[data-status]").forEach((button) => button.classList.remove("active"));
    filterButton.classList.add("active");
    loadOrders();
  }

  if (actionButton) {
    updateOrderStatus(actionButton.dataset.orderId, actionButton.dataset.orderStatus, actionButton);
  }
});

loadOrders();
