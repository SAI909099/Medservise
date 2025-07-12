document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("Please log in first.");
    location.href = "index.html";
    return;
  }

  fetch("http://localhost:8000/api/v1/payments/", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
    .then(res => res.json())
    .then(payments => {
      const tbody = document.querySelector("#payments-table tbody");
      tbody.innerHTML = "";

      payments.forEach((p, i) => {
        const tr = document.createElement("tr");

        const patient = p.appointment?.patient;
        const doctor = p.appointment?.doctor;

        tr.innerHTML = `
          <td>${i + 1}</td>
          <td>${patient ? `${patient.first_name} ${patient.last_name}` : "❌ Unknown"}</td>
          <td>${doctor ? doctor.name : "❌ Unknown"}</td>
          <td>$${parseFloat(p.amount_due).toFixed(2)}</td>
          <td>$${parseFloat(p.amount_paid).toFixed(2)}</td>
          <td>
            <span class="badge ${
              p.status === "paid" ? "bg-success" :
              p.status === "unpaid" ? "bg-danger" : "bg-warning text-dark"
            }">${p.status.toUpperCase()}</span>
          </td>
          <td>${new Date(p.created_at).toLocaleString()}</td>
        `;

        tbody.appendChild(tr);
      });
    })
    .catch(err => {
      console.error("❌ Failed to load payments:", err);
      alert("Could not load payment list.");
    });
});
