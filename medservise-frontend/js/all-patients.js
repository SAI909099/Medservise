document.addEventListener('DOMContentLoaded', async () => {
  const token = localStorage.getItem('access'); // 🔐 Make sure user is logged in
  const tableBody = document.getElementById('patient-table-body');

  try {
    const response = await fetch('http://localhost:8000/api/v1/patients/', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    const patients = await response.json();
    console.log(patients);

    patients.forEach((patient, index) => {
      const tr = document.createElement('tr');

      tr.innerHTML = `
        <td>${patient.id}</td>
        <td>${patient.first_name} ${patient.last_name}</td>
        <td>${patient.phone}</td>
        <td>${patient.latest_doctor || 'N/A'}</td>
        <td>${new Date(patient.created_at).toLocaleString()}</td>
        <td>
          <a href="/medservise-frontend/patient-detail.html?patient_id=${patient.id}" class="btn btn-info btn-sm">Info</a>
        </td>
      `;
      tableBody.appendChild(tr);
    });
  } catch (error) {
    console.error("Error loading patients:", error);
  }
});
