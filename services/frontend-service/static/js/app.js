(() => {
    "use strict";

    const root = document.documentElement;
    const savedTheme = localStorage.getItem("traininghub-theme");
    const preferredTheme = window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";

    const applyTheme = (theme) => {
        root.setAttribute("data-bs-theme", theme);
        document.querySelectorAll(".theme-toggle i").forEach((icon) => {
            icon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
        });
    };

    applyTheme(savedTheme || preferredTheme);

    document.querySelectorAll(".theme-toggle").forEach((button) => {
        button.addEventListener("click", () => {
            const next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
            localStorage.setItem("traininghub-theme", next);
            applyTheme(next);
        });
    });

    const sidebar = document.querySelector(".sidebar");
    const backdrop = document.querySelector(".sidebar-backdrop");
    const closeSidebar = () => {
        sidebar?.classList.remove("open");
        backdrop?.classList.remove("show");
    };

    document.querySelector(".sidebar-toggle")?.addEventListener("click", () => {
        sidebar?.classList.toggle("open");
        backdrop?.classList.toggle("show");
    });
    backdrop?.addEventListener("click", closeSidebar);

    document.querySelectorAll(".password-toggle").forEach((button) => {
        button.addEventListener("click", () => {
            const input = button.closest(".input-wrap")?.querySelector(".password-input");
            if (!input) return;
            input.type = input.type === "password" ? "text" : "password";
            button.querySelector("i").className =
                input.type === "password" ? "bi bi-eye" : "bi bi-eye-slash";
        });
    });

    document.querySelectorAll("[data-progress]").forEach((element) => {
        const progress = Math.max(0, Math.min(100, Number(element.dataset.progress) || 0));
        if (element.classList.contains("achievement-ring")) {
            element.style.setProperty("--ring-progress", `${progress}%`);
        } else {
            requestAnimationFrame(() => {
                element.style.width = `${progress}%`;
            });
        }
    });

    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });

    const chartCanvas = document.getElementById("activityChart");
    if (chartCanvas && window.Chart) {
        const styles = getComputedStyle(root);
        const textColor = styles.getPropertyValue("--muted").trim();
        const lineColor = styles.getPropertyValue("--line").trim();
        new window.Chart(chartCanvas, {
            type: "bar",
            data: {
                labels: ["Apprenants", "Formations", "Inscriptions", "Terminées"],
                datasets: [{
                    data: [
                        Number(chartCanvas.dataset.learners),
                        Number(chartCanvas.dataset.courses),
                        Number(chartCanvas.dataset.enrollments),
                        Number(chartCanvas.dataset.completed),
                    ],
                    backgroundColor: ["#6c4cf5", "#13b8d2", "#f59e42", "#24b47e"],
                    borderRadius: 9,
                    borderSkipped: false,
                    maxBarThickness: 52,
                }],
            },
            options: {
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: {
                        grid: { display: false },
                        border: { display: false },
                        ticks: { color: textColor, font: { size: 11, family: "Manrope" } },
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: lineColor },
                        border: { display: false },
                        ticks: { color: textColor, precision: 0, font: { size: 10 } },
                    },
                },
            },
        });
    }
})();
