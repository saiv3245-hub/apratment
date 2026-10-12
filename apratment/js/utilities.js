const utilityModal = document.getElementById("utilityModal");
const utilityForm = document.getElementById("utilityForm");
const utilityRows = document.getElementById("utilityRows");
const utilityMessage = document.getElementById("utilityMessage");
const utilityNotice = document.getElementById("utilityNotice");
const utilityModalTitle = document.getElementById("utilityModalTitle");
const invoiceContract = document.getElementById("invoiceContract");

let csrfToken = "";
let invoices = [];
let selectedInvoice = null;
let editingInvoice = null;

const modal = bootstrap.Modal.getOrCreateInstance(utilityModal);

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

function selectInvoice(item) {
    selectedInvoice = item;
    document.getElementById("editUtility").disabled = !item;
    document.getElementById("deleteUtility").disabled = !item;
}

function renderInvoices() {
    utilityRows.replaceChildren();

    if (!invoices.length) {
        utilityRows.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">ไม่พบข้อมูลบิล</td></tr>';
        return;
    }

    invoices.forEach(item => {
        const row = utilityRows.insertRow();
        const selectCell = row.insertCell();
        selectCell.className = "text-center";

        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "selectedInvoice";
        radio.className = "form-check-input";
        radio.addEventListener("change", () => selectInvoice(item));
        selectCell.appendChild(radio);

        row.insertCell().textContent = item.invoice_number;
        row.insertCell().textContent = item.billing_month;
        row.insertCell().textContent = item.room_number;
        row.insertCell().textContent = item.tenant_name;
        row.insertCell().textContent = money(item.rent_amount);
        row.insertCell().textContent = money(item.water_amount);
        row.insertCell().textContent = money(item.electric_amount);
        row.insertCell().textContent = money(item.total_amount);
    });
}

async function loadInvoices(message = "") {
    selectInvoice(null);
    const params = new URLSearchParams();
    const search = document.getElementById("searchUtility").value.trim();

    if (search) params.set("q", search);

    try {
        const data = await api(`/api/utilities?${params.toString()}`);
        invoices = data.items || [];
        renderInvoices();

        utilityMessage.textContent = message
            ? `${message} พบ ${invoices.length} รายการ`
            : `พบ ${invoices.length} รายการ`;
    } catch (error) {
        utilityMessage.textContent = error.message;
        utilityMessage.classList.add("text-danger");
    }
}

async function loadContracts() {
    const data = await api("/api/utilities/contracts");
    invoiceContract.innerHTML = '<option value="">เลือกสัญญาเช่า</option>';

    data.items.forEach(item => {
        const option = document.createElement("option");
        option.value = item.contract_id;
        option.textContent = `${item.contract_number} | ห้อง ${item.room_number} | ${item.tenant_name}`;
        option.dataset.rent = item.monthly_rent;
        invoiceContract.appendChild(option);
    });
}

function calculatePreview() {
    const rent = Number(document.getElementById("rentAmount").value || 0);
    const wp = Number(document.getElementById("waterPrevious").value || 0);
    const wc = Number(document.getElementById("waterCurrent").value || 0);
    const wr = Number(document.getElementById("waterRate").value || 0);
    const ep = Number(document.getElementById("electricPrevious").value || 0);
    const ec = Number(document.getElementById("electricCurrent").value || 0);
    const er = Number(document.getElementById("electricRate").value || 0);
    const other = Number(document.getElementById("otherAmount").value || 0);

    const water = Math.max(0, wc - wp) * wr;
    const electric = Math.max(0, ec - ep) * er;
    const total = rent + water + electric + other;

    document.getElementById("utilityPreview").textContent =
        `ค่าน้ำ ${money(water)} บาท | ค่าไฟ ${money(electric)} บาท | รวม ${money(total)} บาท`;
}

invoiceContract.addEventListener("change", () => {
    if (editingInvoice) return;

    const option = invoiceContract.selectedOptions[0];
    if (option && option.value) {
        document.getElementById("rentAmount").value = option.dataset.rent || "";
        calculatePreview();
    }
});

utilityForm.querySelectorAll('input[type="number"]').forEach(input => {
    input.addEventListener("input", calculatePreview);
});

async function openInvoiceForm(item = null) {
    utilityForm.reset();
    utilityNotice.hidden = true;
    editingInvoice = item;
    utilityModalTitle.textContent = item ? "แก้ไขบิล" : "เพิ่มบิล";
    modal.show();

    try {
        await loadContracts();

        if (!item) {
            calculatePreview();
            return;
        }

        const data = await api(`/api/utilities/${item.invoice_id}`);
        editingInvoice = data.item;

        Object.entries(editingInvoice).forEach(([key, value]) => {
            const field = utilityForm.elements.namedItem(key);
            if (field) field.value = value == null ? "" : String(value);
        });

        calculatePreview();
    } catch (error) {
        utilityNotice.className = "alert alert-danger mt-3 mb-0";
        utilityNotice.textContent = error.message;
        utilityNotice.hidden = false;
    }
}

document.getElementById("addUtility").addEventListener("click", () => openInvoiceForm());

document.getElementById("editUtility").addEventListener("click", () => {
    if (selectedInvoice) openInvoiceForm(selectedInvoice);
});

document.getElementById("deleteUtility").addEventListener("click", async () => {
    if (!selectedInvoice) return;
    if (!confirm(`ยืนยันลบบิล ${selectedInvoice.invoice_number}?`)) return;

    try {
        const data = await api(`/api/utilities/${selectedInvoice.invoice_id}`, {
            method: "DELETE",
            body: JSON.stringify({})
        });
        await loadInvoices(data.message);
    } catch (error) {
        utilityMessage.textContent = error.message;
        utilityMessage.classList.add("text-danger");
    }
});

utilityForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (!utilityForm.reportValidity()) return;

    try {
        const data = await api(
            editingInvoice
                ? `/api/utilities/${editingInvoice.invoice_id}`
                : "/api/utilities",
            {
                method: editingInvoice ? "PUT" : "POST",
                body: JSON.stringify(Object.fromEntries(new FormData(utilityForm)))
            }
        );

        modal.hide();
        await loadInvoices(data.message);
    } catch (error) {
        utilityNotice.className = "alert alert-danger mt-3 mb-0";
        utilityNotice.textContent = error.message;
        utilityNotice.hidden = false;
    }
});

document.getElementById("utilityFilter").addEventListener("submit", event => {
    event.preventDefault();
    loadInvoices();
});

document.getElementById("clearUtilityFilters").addEventListener("click", () => {
    document.getElementById("utilityFilter").reset();
    loadInvoices();
});

(async function start() {
    csrfToken = (await api("/api/csrf")).token;
    await loadInvoices();
})();