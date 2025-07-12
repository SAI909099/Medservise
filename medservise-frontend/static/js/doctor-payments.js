document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  const tbody = document.querySelector("#payments-table tbody");

  function loadDoctorPayments() {
    fetch("http://localhost:8000/api/v1/doctor-payments/", {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to load doctor payments");
        return res.json();
      })
      .then(data => {
        tbody.innerHTML = "";
        data.forEach(payment => {
          const tr = document.createElement("tr");

          const patientName = `${payment.patient_first_name || ''} ${payment.patient_last_name || ''}`.trim() || "Unknown patient";
          const doctorName = `${payment.doctor_first_name || ''} ${payment.doctor_last_name || ''}`.trim() || "Unknown doctor";

          const amountNum = Number(payment.amount_paid);
          const amount = isNaN(amountNum) ? "N/A" : amountNum.toLocaleString();

          const dateStr = payment.created_at ? new Date(payment.created_at).toLocaleString() : "Unknown date";

          const notes = payment.notes || "";

          tr.innerHTML = `
            <td>${patientName}</td>
            <td>${doctorName}</td>
            <td>${amount} so'm</td>
            <td>${dateStr}</td>
            <td>${notes}</td>
          `;
          tbody.appendChild(tr);
        });
      })
      .catch(err => {
        tbody.innerHTML = `<tr><td colspan="5" class="text-danger">Error loading payments: ${err.message}</td></tr>`;
        console.error(err);
      });
  }

  loadDoctorPayments();
});
