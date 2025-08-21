document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");

  if (!token) {
    alert("Iltimos, tizimga kiring.");
    location.href = "index.html";
    return;
  }

  fetch("http://89.39.95.150/api/v1/payments/", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
    .then(res => {
      if (!res.ok) throw new Error("To‘lovlar ro‘yxatini yuklab bo‘lmadi");
      return res.json();
    })
    .then(payments => {
      const tbody = document.querySelector("#payments-table tbody");
      tbody.innerHTML = "";

      payments.forEach((p, i) => {
        const tr = document.createElement("tr");

        const patient = p.appointment?.patient;
        const doctor = p.appointment?.doctor;

        tr.innerHTML = `
          <td>${i + 1}</td>
          <td>${patient ? `${patient.first_name} ${patient.last_name}` : "❌ Nomaʼlum"}</td>
          <td>${doctor ? doctor.name : "❌ Nomaʼlum"}</td>
          <td>${parseFloat(p.amount_due).toLocaleString()} so'm</td>
          <td>${parseFloat(p.amount_paid).toLocaleString()} so'm</td>
          <td>
            <span class="badge ${
              p.status === "paid" ? "bg-success" :
              p.status === "unpaid" ? "bg-danger" : "bg-warning text-dark"
            }">${p.status.toUpperCase()}</span>
          </td>
          <td>${new Date(p.created_at).toLocaleString("uz-UZ")}</td>
        `;

        tbody.appendChild(tr);
      });
    })
    .catch(err => {
      console.error("❌ To‘lovlar yuklanmadi:", err);
      alert("❌ To‘lovlar ro‘yxatini yuklab bo‘lmadi.");
    });
});
