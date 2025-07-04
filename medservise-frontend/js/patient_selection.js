document.addEventListener("DOMContentLoaded", async function() {
  // Check authentication
  if (!localStorage.getItem("token")) {
    alert("Please login first");
    window.location.href = "/";
    return;
  }

  // Load initial patient data
  loadPatients("today");

  // Setup search button
  document.getElementById("search-btn").addEventListener("click", function() {
    const name = document.getElementById("name-search").value;
    const phone = document.getElementById("phone-search").value;
    const dateRange = document.getElementById("date-range").value;
    searchPatients(name, phone, dateRange);
  });
});

async function loadPatients(dateRange = "today") {
  try {
    let url = `http://localhost:8000/api/v1/patients/`;
    const params = new URLSearchParams();

    // Add date range filter
    if (dateRange !== "all") {
      let startDate = new Date();

      if (dateRange === "3days") {
        startDate.setDate(startDate.getDate() - 3);
      } else if (dateRange === "7days") {
        startDate.setDate(startDate.getDate() - 7);
      } else { // today
        // No adjustment needed
      }

      params.append("start_date", startDate.toISOString().split('T')[0]);
    }

    const response = await authFetch(`${url}?${params.toString()}`);

    if (!response.ok) {
      throw new Error("Failed to load patients");
    }

    const patients = await response.json();
    renderPatients(patients);
  } catch (error) {
    console.error("Error loading patients:", error);
    alert(`Error: ${error.message}`);
  }
}

async function searchPatients(name, phone, dateRange) {
  try {
    const params = new URLSearchParams();

    if (name) params.append("name", name);
    if (phone) params.append("phone", phone);

    // Add date range filter
    if (dateRange !== "all") {
      let startDate = new Date();

      if (dateRange === "3days") {
        startDate.setDate(startDate.getDate() - 3);
      } else if (dateRange === "7days") {
        startDate.setDate(startDate.getDate() - 7);
      }

      params.append("start_date", startDate.toISOString().split('T')[0]);
    }

    const response = await authFetch(`http://localhost:8000/api/v1/patients/?${params.toString()}`);

    if (!response.ok) {
      throw new Error("Search failed");
    }

    const patients = await response.json();
    renderPatients(patients);
  } catch (error) {
    console.error("Search error:", error);
    alert(`Error: ${error.message}`);
  }
}

function renderPatients(patients) {
  const tbody = document.getElementById("patients-body");
  tbody.innerHTML = "";

  if (!patients || patients.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="text-center">No patients found</td>
      </tr>
    `;
    return;
  }

  patients.forEach(patient => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${patient.id}</td>
      <td>${patient.first_name} ${patient.last_name}</td>
      <td>${patient.phone}</td>
      <td class="${patient.balance > 0 ? 'balance-positive' : 'balance-zero'}">
        $${patient.balance.toFixed(2)}
      </td>
      <td>${new Date(patient.last_visit).toLocaleDateString()}</td>
      <td>
        <button class="btn btn-sm btn-primary" 
                onclick="selectPatient(${patient.id})">
          Select for Payment
        </button>
      </td>
    `;
    tbody.appendChild(row);
  });
}

function selectPatient(patientId) {
  window.location.href = `/cash_registration.html?patient_id=${patientId}`;
}