document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("Please log in first.");
    location.href = "index.html";
    return;
  }

  fetch("http://localhost:8000/api/v1/register-patient/", {
    headers: { Authorization: `Bearer ${token}` }
  })
    .then(res => res.json())
    .then(patients => {
      const tbody = document.getElementById("patient-table-body");
      patients.forEach((patient, index) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${index + 1}</td>
          <td>${patient.first_name} ${patient.last_name}</td>
          <td>${patient.phone}</td>
          <td>${patient.patients_doctor_name || "—"}</td>
          <td>${new Date(patient.created_at).toLocaleString()}</td>
          <td>
            <a href="patient-detail.html?patient_id=${patient.id}" class="btn btn-info btn-sm">Info</a>
          </td>
        `;
        tbody.appendChild(tr);
      });
    })
    .catch(err => {
      console.error("Error loading patients", err);
      alert("Failed to load patients.");
    });
});
