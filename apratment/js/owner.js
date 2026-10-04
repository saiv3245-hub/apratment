(() => {
    const totalRooms = document.getElementById("totalRooms");
    const availableRooms = document.getElementById("availableRooms");
    const activeTenants = document.getElementById("activeTenants");
    const overdueBills = document.getElementById("overdueBills");
    const invoiceRows = document.getElementById("invoiceRows");
    const repairList = document.getElementById("repairList");
    const dashboardMessage = document.getElementById("dashboardMessage");

    if (!totalRooms || !availableRooms || !activeTenants || !overdueBills || !invoiceRows || !repairList) {
        return;
    }

    function createInvoiceStatus(status) {
        const value = String(status || "").toUpperCase();
        const badge = document.createElement("span");

        if (value === "PAID") {
            badge.className = "badge text-bg-success";
            badge.textContent = "ชำระแล้ว";
        } else if (value === "PARTIAL") {
            badge.className = "badge text-bg-warning";
            badge.textContent = "ชำระบางส่วน";
        } else {
            badge.className = "badge text-bg-danger";
            badge.textContent = "ยังไม่ชำระ";
        }

        return badge;
    }

    function renderInvoices(invoices) {
        invoiceRows.replaceChildren();

        if (invoices.length === 0) {
            const row = invoiceRows.insertRow();
            const cell = row.insertCell();
            cell.colSpan = 4;
            cell.className = "text-center text-muted py-4";
            cell.textContent = "ยังไม่มีข้อมูลบิล";
            return;
        }

        invoices.forEach(invoice => {
            const row = invoiceRows.insertRow();
            row.insertCell().textContent = invoice.room_number || "—";
            row.insertCell().textContent = invoice.tenant_name || "—";

            const amountCell = row.insertCell();
            amountCell.textContent = Number(invoice.total_amount || 0).toLocaleString("th-TH", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });

            row.insertCell().appendChild(createInvoiceStatus(invoice.payment_status));
        });
    }

    function getRepairStatus(status) {
        const value = String(status || "").toUpperCase();

        if (value === "PENDING") {
            return ["รอดำเนินการ", "text-bg-warning"];
        }
        if (value === "IN_PROGRESS") {
            return ["กำลังดำเนินการ", "text-bg-primary"];
        }
        if (value === "COMPLETED") {
            return ["เสร็จสิ้น", "text-bg-success"];
        }
        if (value === "CANCELLED") {
            return ["ยกเลิก", "text-bg-secondary"];
        }

        return [status || "—", "text-bg-secondary"];
    }

    function getPriority(priority) {
        const value = String(priority || "").toUpperCase();

        if (value === "URGENT") {
            return "เร่งด่วนมาก";
        }
        if (value === "HIGH") {
            return "เร่งด่วน";
        }
        if (value === "NORMAL") {
            return "ปกติ";
        }
        if (value === "LOW") {
            return "ต่ำ";
        }

        return priority || "—";
    }

    function renderRepairs(repairs) {
        repairList.replaceChildren();

        if (repairs.length === 0) {
            const message = document.createElement("p");
            message.className = "text-center text-muted py-4 mb-0";
            message.textContent = "ไม่มีรายการแจ้งซ่อมที่กำลังดำเนินการ";
            repairList.appendChild(message);
            return;
        }

        repairs.forEach(repair => {
            const item = document.createElement("div");
            item.className = "repair-item";

            const detail = document.createElement("div");
            const title = document.createElement("strong");
            const info = document.createElement("span");

            title.textContent = `ห้อง ${repair.room_number || "—"} - ${repair.title || "—"}`;
            info.textContent = `${repair.request_number || "—"} • ${getPriority(repair.priority)}`;

            detail.appendChild(title);
            detail.appendChild(info);

            const [statusText, statusClass] = getRepairStatus(repair.status);
            const badge = document.createElement("span");
            badge.className = `badge ${statusClass}`;
            badge.textContent = statusText;

            item.appendChild(detail);
            item.appendChild(badge);
            repairList.appendChild(item);
        });
    }

    function showError(message) {
        totalRooms.textContent = "—";
        availableRooms.textContent = "—";
        activeTenants.textContent = "—";
        overdueBills.textContent = "—";

        invoiceRows.innerHTML = `
            <tr>
                <td colspan="4" class="text-center text-danger py-4">${message}</td>
            </tr>
        `;

        repairList.innerHTML = `
            <p class="text-center text-danger py-4 mb-0">${message}</p>
        `;

        if (dashboardMessage) {
            dashboardMessage.textContent = message;
            dashboardMessage.classList.add("text-danger");
        }
    }

    async function loadDashboard() {
        if (dashboardMessage) {
            dashboardMessage.textContent = "กำลังโหลดข้อมูลจากฐานข้อมูล...";
            dashboardMessage.classList.remove("text-danger");
        }

        try {
            const response = await fetch("/api/owner/dashboard", {
                credentials: "same-origin",
                cache: "no-store"
            });

            const data = await response.json().catch(() => ({}));

            if (!response.ok) {
                throw new Error(data.error || "โหลดข้อมูลหน้าหลักไม่สำเร็จ");
            }

            totalRooms.textContent = data.total_rooms ?? 0;
            availableRooms.textContent = data.available_rooms ?? 0;
            activeTenants.textContent = data.active_tenants ?? 0;
            overdueBills.textContent = data.overdue_bills ?? 0;

            renderInvoices(data.invoices || []);
            renderRepairs(data.repairs || []);

            if (dashboardMessage) {
                dashboardMessage.textContent = "ข้อมูลจากฐานข้อมูล PostgreSQL";
            }
        } catch (error) {
            showError(error.message);
        }
    }

    loadDashboard();
})();