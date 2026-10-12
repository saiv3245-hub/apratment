const tenantModal = document.getElementById("tenantModal");
const tenantForm = document.getElementById("tenantForm");
const tenantRows = document.getElementById("tenantRows");
const tenantFilter = document.getElementById("tenantFilter");
const tenantFilterMessage = document.getElementById("tenantFilterMessage");
const clearTenantFilters = document.getElementById("clearTenantFilters");
const addTenant = document.getElementById("addTenant");
const viewTenant = document.getElementById("viewTenant");
const editTenant = document.getElementById("editTenant");
const deleteTenant = document.getElementById("deleteTenant");
const tenantNotice = document.getElementById("tenantNotice");
const tenantUser = document.getElementById("tenantUser");
const tenantModalTitle = document.getElementById("tenantModalTitle");
const tenantFormHelp = document.getElementById("tenantFormHelp");
const saveTenant = document.querySelector('[type="submit"][form="tenantForm"]');

let csrfToken = "";
let tenantList = [];
let selectedTenant = null;
let editingTenant = null;
let viewingTenant = false;

const modal = bootstrap.Modal.getOrCreateInstance(tenantModal);

async function api(url, options = {}) {
    const settings = {
        credentials: "same-origin",
        cache: "no-store",
        ...options
    };

    settings.headers = {...(options.headers || {})};

    if (settings.body) {
        settings.headers["Content-Type"] = "application/json";
        settings.headers["X-CSRF-Token"] = csrfToken;
    }

    const response = await fetch(url, settings);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || "ทำรายการไม่สำเร็จ");
    }

    return data;
}

function showMessage(text, error = false) {
    tenantFilterMessage.textContent = text;
    tenantFilterMessage.classList.toggle("text-danger", error);
}

function setSelected(tenant) {
    selectedTenant = tenant;
    viewTenant.disabled = !tenant;
    editTenant.disabled = !tenant;
    deleteTenant.disabled = !tenant;
}

function renderTenants() {
    tenantRows.replaceChildren();

    if (tenantList.length === 0) {
        const row = tenantRows.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 6;
        cell.className = "text-center text-muted py-4";
        cell.textContent = "ไม่พบข้อมูลผู้เช่า";
        return;
    }

    tenantList.forEach(tenant => {
        const row = tenantRows.insertRow();

        const selectCell = row.insertCell();
        selectCell.className = "text-center";

        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "selectedTenant";
        radio.className = "form-check-input";
        radio.addEventListener("change", () => setSelected(tenant));
        selectCell.appendChild(radio);

        row.insertCell().textContent = tenant.tenant_code;
        row.insertCell().textContent = `${tenant.first_name} ${tenant.last_name}`;
        row.insertCell().textContent = tenant.phone;
        row.insertCell().textContent = tenant.email;

        const statusCell = row.insertCell();
        const badge = document.createElement("span");
        badge.className = tenant.is_active ? "badge text-bg-success" : "badge text-bg-secondary";
        badge.textContent = tenant.is_active ? "เปิดใช้งาน" : "ปิดใช้งาน";
        statusCell.appendChild(badge);
    });
}

async function loadTenants(message = "") {
    setSelected(null);
    showMessage("กำลังโหลดข้อมูลผู้เช่า...");

    const params = new URLSearchParams();
    const search = document.getElementById("searchTenant").value.trim();
    const status = document.getElementById("tenantStatusFilter").value;

    if (search) params.set("q", search);
    if (status) params.set("status", status);

    try {
        const data = await api(`/api/tenants?${params.toString()}`);
        tenantList = data.items || [];
        renderTenants();

        if (message) {
            showMessage(`${message} พบ ${tenantList.length} รายการ`);
        } else {
            showMessage(`พบ ${tenantList.length} รายการ`);
        }
    } catch (error) {
        tenantList = [];
        renderTenants();
        showMessage(error.message, true);
    }
}

async function loadTenantUsers(currentTenantId = 0, currentUserId = "") {
    tenantUser.disabled = true;
    tenantUser.replaceChildren();

    const loadingOption = document.createElement("option");
    loadingOption.value = "";
    loadingOption.textContent = "กำลังโหลดบัญชีผู้ใช้งาน...";
    tenantUser.appendChild(loadingOption);

    try {
        const data = await api(`/api/tenant-users?tenant_id=${currentTenantId}`);

        tenantUser.replaceChildren();

        const first = document.createElement("option");
        first.value = "";
        first.textContent = "เลือกบัญชีผู้ใช้งาน";
        tenantUser.appendChild(first);

        data.items.forEach(user => {
            const option = document.createElement("option");
            option.value = user.user_id;
            option.textContent = user.user_name;
            tenantUser.appendChild(option);
        });

        if (currentUserId) {
            tenantUser.value = String(currentUserId);
        }

        if (tenantUser.options.length === 1) {
            tenantUser.disabled = true;
            first.textContent = "ไม่มีบัญชีผู้เช่าที่ยังไม่ได้เชื่อมข้อมูล";
        } else {
            tenantUser.disabled = false;
        }

        return true;
    } catch (error) {
        tenantUser.replaceChildren();

        const option = document.createElement("option");
        option.value = "";
        option.textContent = "โหลดบัญชีผู้ใช้งานไม่สำเร็จ";
        tenantUser.appendChild(option);
        tenantUser.disabled = true;

        tenantNotice.className = "alert alert-danger mt-3 mb-0";
        tenantNotice.textContent = error.message;
        tenantNotice.hidden = false;

        return false;
    }
}

function setFormDisabled(disabled) {
    tenantForm.querySelectorAll("input, select, textarea").forEach(field => {
        if (field.type !== "hidden") {
            field.disabled = disabled;
        }
    });
}

async function openTenantForm(mode) {
    if (mode !== "add" && !selectedTenant) {
        return;
    }

    tenantForm.reset();
    tenantNotice.hidden = true;
    tenantNotice.textContent = "";
    editingTenant = null;
    viewingTenant = mode === "view";

    if (mode === "add") {
        tenantModalTitle.textContent = "เพิ่มผู้เช่า";
        tenantFormHelp.textContent = "เลือกบัญชีผู้ใช้งาน แล้วกรอกข้อมูลผู้เช่า";
        setFormDisabled(false);
        saveTenant.hidden = false;

        modal.show();
        await loadTenantUsers();
        return;
    }

    modal.show();

    try {
        const data = await api(`/api/tenants/${selectedTenant.tenant_id}`);
        editingTenant = data.item;

        tenantModalTitle.textContent = viewingTenant ? "ข้อมูลผู้เช่า" : "แก้ไขผู้เช่า";
        tenantFormHelp.textContent = viewingTenant
            ? "รายละเอียดข้อมูลผู้เช่า"
            : "แก้ไขข้อมูลแล้วกดบันทึก";

        setFormDisabled(false);
        await loadTenantUsers(editingTenant.tenant_id, editingTenant.user_id);

        Object.entries(editingTenant).forEach(([key, value]) => {
            const field = tenantForm.elements.namedItem(key);

            if (field) {
                field.value = value == null ? "" : String(value);
            }
        });

        document.getElementById("tenantStatus").value = editingTenant.is_active ? "true" : "false";

        if (viewingTenant) {
            setFormDisabled(true);
            saveTenant.hidden = true;
        } else {
            saveTenant.hidden = false;
        }
    } catch (error) {
        tenantNotice.className = "alert alert-danger mt-3 mb-0";
        tenantNotice.textContent = error.message;
        tenantNotice.hidden = false;
    }
}

addTenant.addEventListener("click", function () {
    openTenantForm("add");
});

viewTenant.addEventListener("click", function () {
    openTenantForm("view");
});

editTenant.addEventListener("click", function () {
    openTenantForm("edit");
});

deleteTenant.addEventListener("click", async function () {
    if (!selectedTenant) {
        return;
    }

    if (!confirm(`ยืนยันลบผู้เช่า ${selectedTenant.tenant_code}?`)) {
        return;
    }

    try {
        const data = await api(`/api/tenants/${selectedTenant.tenant_id}`, {
            method: "DELETE",
            body: JSON.stringify({})
        });

        await loadTenants(data.message);
    } catch (error) {
        showMessage(error.message, true);
    }
});

tenantForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    if (!tenantForm.reportValidity()) {
        return;
    }

    if (tenantUser.disabled || !tenantUser.value) {
        tenantNotice.className = "alert alert-danger mt-3 mb-0";
        tenantNotice.textContent = "กรุณาเลือกบัญชีผู้ใช้งานสำหรับผู้เช่า";
        tenantNotice.hidden = false;
        return;
    }

    const body = Object.fromEntries(new FormData(tenantForm));
    body.user_id = tenantUser.value;

    tenantNotice.hidden = true;
    saveTenant.disabled = true;

    try {
        const data = await api(
            editingTenant
                ? `/api/tenants/${editingTenant.tenant_id}`
                : "/api/tenants",
            {
                method: editingTenant ? "PUT" : "POST",
                body: JSON.stringify(body)
            }
        );

        modal.hide();
        await loadTenants(data.message);
    } catch (error) {
        tenantNotice.className = "alert alert-danger mt-3 mb-0";
        tenantNotice.textContent = error.message;
        tenantNotice.hidden = false;
    } finally {
        saveTenant.disabled = false;
    }
});

tenantFilter.addEventListener("submit", function (event) {
    event.preventDefault();
    loadTenants();
});

clearTenantFilters.addEventListener("click", function () {
    tenantFilter.reset();
    loadTenants();
});

async function start() {
    try {
        const data = await api("/api/csrf");
        csrfToken = data.token;
        await loadTenants();
    } catch (error) {
        showMessage(error.message, true);
    }
}

start();