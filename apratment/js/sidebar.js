const sidebarToggle = document.getElementById("sidebarToggle");
const sidebarMenu = document.getElementById("sidebarMenu");

if (sidebarToggle && sidebarMenu) {
    sidebarToggle.addEventListener("click", function () {
        const isOpen = sidebarMenu.classList.toggle("active");
        sidebarMenu.inert = !isOpen;
        sidebarToggle.setAttribute("aria-expanded", String(isOpen));
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && sidebarMenu.classList.contains("active")) {
            sidebarToggle.focus();
            sidebarMenu.classList.remove("active");
            sidebarMenu.inert = true;
            sidebarToggle.setAttribute("aria-expanded", "false");
        }
    });
}