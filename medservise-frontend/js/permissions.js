
(function checkPermissions() {
  const userRole = localStorage.getItem("role");
  const currentPage = window.location.pathname.split("/").pop();

  const rolePages = {
    admin: ["*"],
    doctor: ["doctor.html", "doctor-patient-rooms.html", "index.html"],
    accountant: ["accounting-dashboard.html"],
    registration: [
      "registration.html",
      "treatment-registration.html",
      "treatment-room-management.html",
      "turn-display.html"
    ],
    casher: [
      "cash-register.html",
      "treatment-room-payments.html",
      "turn-display.html"
    ]
  };

  function isAllowed(role, page) {
    if (!role) return false;
    if (role === "admin") return true;
    const allowedPages = rolePages[role] || [];
    return allowedPages.includes(page);
  }

  if (!isAllowed(userRole, currentPage)) {
    alert("⛔ Sizda bu sahifaga ruxsat yo‘q!");
    window.location.href = "index.html";
  }
})();
