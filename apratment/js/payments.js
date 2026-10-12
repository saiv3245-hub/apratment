const paymentModal = document.getElementById("paymentModal");
const paymentForm = document.getElementById("paymentForm");
const paymentRows = document.getElementById("paymentRows");
const paymentMessage = document.getElementById("paymentMessage");
const paymentNotice = document.getElementById("paymentNotice");

let csrfToken = "";
let payments = [];
let selectedPayment = null;
let editingPayment = null;

const modal = bootstrap.Modal.getOrCreateInstance(paymentModal);

async function api(url, options = {}) {
    const settings = {credentials: "same-origin", cache: "no-store", ...options};
    settings.headers = {...(options.headers || {})};

    if (settings.body) {
        settings.headers["Content-Type"] = "application/json";
        settings.headers["X-CSRF-Token"] = csrfToken;
    }

    const response = await fetch(url, settings);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "ทำรายการไม่สำเร็จ");
    return data;
}

function money(value) {
    return Number(value || 0).toLocaleString("th-TH", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function selectPayment(item) {
    selectedPayment = item;
    document.getElementById("editPayment").disabled = !item;
}

function renderPayments() {
    paymentRows.replaceChildren();

    if (!payments.length) {
        paymentRows.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">ไม่พบข้อมูลการชำระเงิน</td></tr>';
        return;
    }

    payments.forEach(item => {
        const row = paymentRows.insertRow();
        const selectCell = row.insertCell();
        selectCell.className = "text-center";

        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "selectedPayment";
        radio.className = "form-check-input";
        radio.addEventListener("change", () => selectPayment(item));
        selectCell.appendChild(radio);

        row.insertCell().textContent = item.invoice_number;
        row.insertCell().textContent = item.room_number;
        row.insertCell().textContent = item.tenant_name;
        row.insertCell().textContent = money(item.total_amount);
        row.insertCell().textContent = money(item.amount_paid);
        row.insertCell().textContent = money(Number(item.total_amount) - Number(item.amount_paid));
        row.insertCell().textContent = item.payment_method || "—";
        row.insertCell().textContent = {
            UNPAID: "ยังไม่ชำระ",
            PARTIAL: "ชำระบางส่วน",
            PAID: "ชำระแล้ว"
        }[item.payment_status] || item.payment_status;
    });
}

async function loadPayments(message = "") {
    selectPayment(null);

    const params = new URLSearchParams();
    const search = document.getElementById("searchPayment").value.trim();
    const status = document.getElementById("paymentStatusFilter").value;

    if (search) params.set("q", search);
    if (status) params.set("status", status);

    try {
        const data = await api(`/api/payments?${params.toString()}`);
        payments = data.items || [];
        renderPayments();

        paymentMessage.textContent = message
            ? `${message} พบ ${payments.length} รายการ`
            : `พบ ${payments.length} รายการ`;
    } catch (error) {
        paymentMessage.textContent = error.message;
        paymentMessage.classList.add("text-danger");
    }
}

async function openPaymentForm() {
    if (!selectedPayment) return;

    paymentForm.reset();
    paymentNotice.hidden = true;
    modal.show();

    try {
        const data = await api(`/api/payments/${selectedPayment.invoice_id}`);
        editingPayment = data.item;

        document.getElementById("paymentInvoiceInfo").textContent =
            `${editingPayment.invoice_number} | ห้อง ${editingPayment.room_number} | ${editingPayment.tenant_name} | ยอดรวม ${money(editingPayment.total_amount)} บาท`;

        ["amount_paid", "payment_method", "receipt_number", "note"].forEach(key => {
            const field = paymentForm.elements.namedItem(key);
            if (field) field.value = editingPayment[key] == null ? "" : String(editingPayment[key]);
        });

        document.getElementById("amountPaid").max = editingPayment.total_amount;
    } catch (error) {
        paymentNotice.className = "alert alert-danger mt-3 mb-0";
        paymentNotice.textContent = error.message;
        paymentNotice.hidden = false;
    }
}

document.getElementById("editPayment").addEventListener("click", openPaymentForm);

paymentForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (!paymentForm.reportValidity() || !editingPayment) return;

    try {
        const data = await api(`/api/payments/${editingPayment.invoice_id}`, {
            method: "PUT",
            body: JSON.stringify(Object.fromEntries(new FormData(paymentForm)))
        });

        modal.hide();
        await loadPayments(data.message);
    } catch (error) {
        paymentNotice.className = "alert alert-danger mt-3 mb-0";
        paymentNotice.textContent = error.message;
        paymentNotice.hidden = false;
    }
});

document.getElementById("paymentFilter").addEventListener("submit", event => {
    event.preventDefault();
    loadPayments();
});

document.getElementById("clearPaymentFilters").addEventListener("click", () => {
    document.getElementById("paymentFilter").reset();
    loadPayments();
});

(async function start() {
    csrfToken = (await api("/api/csrf")).token;
    await loadPayments();
})();