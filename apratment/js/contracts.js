const contractModal = document.getElementById("contractModal");
const contractForm = document.getElementById("contractForm");
const contractRows = document.getElementById("contractRows");
const contractMessage = document.getElementById("contractMessage");
const contractNotice = document.getElementById("contractNotice");
const contractModalTitle = document.getElementById("contractModalTitle");
const contractTenant = document.getElementById("contractTenant");
const contractRoom = document.getElementById("contractRoom");

let csrfToken = "";
let contracts = [];
let selectedContract = null;
let editingContract = null;

const modal = bootstrap.Modal.getOrCreateInstance(contractModal);

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

function selectContract(item) {
    selectedContract = item;
    document.getElementById("editContract").disabled = !item;
    document.getElementById("deleteContract").disabled = !item;
}

function renderContracts() {
    contractRows.replaceChildren();

    if (!contracts.length) {
        contractRows.innerHTML = '<tr><td colspan="8" class="text-center text-muted py-4">ไม่พบข้อมูลสัญญาเช่า</td></tr>';
        return;
    }

    contracts.forEach(item => {
        const row = contractRows.insertRow();
        const selectCell = row.insertCell();
        selectCell.className = "text-center";

        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "selectedContract";
        radio.className = "form-check-input";
        radio.addEventListener("change", () => selectContract(item));
        selectCell.appendChild(radio);

        row.insertCell().textContent = item.contract_number;
        row.insertCell().textContent = item.room_number;
        row.insertCell().textContent = item.tenant_name;
        row.insertCell().textContent = item.start_date;
        row.insertCell().textContent = item.end_date || "—";
        row.insertCell().textContent = money(item.monthly_rent);
        row.insertCell().textContent = {
            ACTIVE: "ใช้งาน",
            ENDED: "สิ้นสุด",
            CANCELLED: "ยกเลิก"
        }[item.contract_status] || item.contract_status;
    });
}

async function loadContracts(message = "") {
    selectContract(null);
    const params = new URLSearchParams();
    const search = document.getElementById("searchContract").value.trim();
    const status = document.getElementById("contractStatusFilter").value;

    if (search) params.set("q", search);
    if (status) params.set("status", status);

    try {
        const data = await api(`/api/contracts?${params.toString()}`);
        contracts = data.items || [];
        renderContracts();
        contractMessage.textContent = message
            ? `${message} พบ ${contracts.length} รายการ`
            : `พบ ${contracts.length} รายการ`;
    } catch (error) {
        contractMessage.textContent = error.message;
        contractMessage.classList.add("text-danger");
    }
}

async function loadOptions() {
    const data = await api("/api/contracts/options");

    contractTenant.innerHTML = '<option value="">เลือกผู้เช่า</option>';
    data.tenants.forEach(tenant => {
        const option = document.createElement("option");
        option.value = tenant.tenant_id;
        option.textContent = `${tenant.tenant_code} - ${tenant.first_name} ${tenant.last_name}`;
        contractTenant.appendChild(option);
    });

    contractRoom.innerHTML = '<option value="">เลือกห้องพัก</option>';
    data.rooms.forEach(room => {
        const option = document.createElement("option");
        option.value = room.room_id;
        option.textContent = `${room.room_number} (${room.status})`;
        option.dataset.rent = room.monthly_rent;
        option.dataset.deposit = room.deposit_amount;
        contractRoom.appendChild(option);
    });
}

contractRoom.addEventListener("change", () => {
    if (editingContract) return;
    const option = contractRoom.selectedOptions[0];
    if (!option || !option.value) return;

    document.getElementById("monthlyRent").value = option.dataset.rent || "";
    document.getElementById("depositAmount").value = option.dataset.deposit || "";
});

async function openContractForm(item = null) {
    contractForm.reset();
    contractNotice.hidden = true;
    editingContract = item;
    contractModalTitle.textContent = item ? "แก้ไขสัญญาเช่า" : "เพิ่มสัญญาเช่า";
    modal.show();

    try {
        await loadOptions();

        if (!item) return;

        const data = await api(`/api/contracts/${item.contract_id}`);
        editingContract = data.item;

        Object.entries(editingContract).forEach(([key, value]) => {
            const field = contractForm.elements.namedItem(key);
            if (field) field.value = value == null ? "" : String(value);
        });
    } catch (error) {
        contractNotice.className = "alert alert-danger mt-3 mb-0";
        contractNotice.textContent = error.message;
        contractNotice.hidden = false;
    }
}

document.getElementById("addContract").addEventListener("click", () => openContractForm());

document.getElementById("editContract").addEventListener("click", () => {
    if (selectedContract) openContractForm(selectedContract);
});

document.getElementById("deleteContract").addEventListener("click", async () => {
    if (!selectedContract) return;
    if (!confirm(`ยืนยันลบสัญญา ${selectedContract.contract_number}?`)) return;

    try {
        const data = await api(`/api/contracts/${selectedContract.contract_id}`, {
            method: "DELETE",
            body: JSON.stringify({})
        });
        await loadContracts(data.message);
    } catch (error) {
        contractMessage.textContent = error.message;
        contractMessage.classList.add("text-danger");
    }
});

contractForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (!contractForm.reportValidity()) return;

    try {
        const data = await api(
            editingContract
                ? `/api/contracts/${editingContract.contract_id}`
                : "/api/contracts",
            {
                method: editingContract ? "PUT" : "POST",
                body: JSON.stringify(Object.fromEntries(new FormData(contractForm)))
            }
        );

        modal.hide();
        await loadContracts(data.message);
    } catch (error) {
        contractNotice.className = "alert alert-danger mt-3 mb-0";
        contractNotice.textContent = error.message;
        contractNotice.hidden = false;
    }
});

document.getElementById("contractFilter").addEventListener("submit", event => {
    event.preventDefault();
    loadContracts();
});

document.getElementById("clearContractFilters").addEventListener("click", () => {
    document.getElementById("contractFilter").reset();
    loadContracts();
});

(async function start() {
    csrfToken = (await api("/api/csrf")).token;
    await loadContracts();
})();