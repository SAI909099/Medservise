const token = localStorage.getItem("token");
const patientListDiv = document.getElementById("patient-list");
const searchInput = document.getElementById("search-input");
const yearFilter = document.getElementById("year-filter");

let allPatients = [];

function fetchPatients() {
  fetch("http://localhost:8000/api/v1/patients/", {
    headers: { Authorization: `Bearer ${token}` }
  })
    .then(res => res.json())
    .then(patients => {
      allPatients = patients;
      populateYearFilter(patients);
      displayPatients(patients);
    })
    .catch(err => {
      console.error("❌ Failed to fetch patients", err);
      patientListDiv.innerHTML = "<p>❌ Error loading patients</p>";
    });
}

function populateYearFilter(patients) {
  const years = [...new Set(patients.map(p => new Date(p.created_at).getFullYear()))];
  years.sort((a, b) => b - a); // Newest first
  years.forEach(y => {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = y;
    yearFilter.appendChild(opt);
  });
}

function displayPatients(patients) {
  if (!patients.length) {
    patientListDiv.innerHTML = "<p>No patients found.</p>";
    return;
  }

  patientListDiv.innerHTML = "";
  patients.forEach(p => {
    const div = document.createElement("div");
    div.className = "border p-2 mb-3 rounded";
    div.innerHTML = `
      <h5>${p.first_name ?? "?"} ${p.last_name ?? "?"}</h5>
      <p><strong>Phone:</strong> ${p.phone ?? "N/A"}</p>
      <p><strong>Registered:</strong> ${new Date(p.created_at).toLocaleString()}</p>
      <a class="btn btn-sm btn-outline-info" href="patient-detail.html?patient_id=${p.id}">🔎 View Info</a>
    `;
    patientListDiv.appendChild(div);
  });
}

function applyFilters() {
  const searchTerm = searchInput.value.toLowerCase();
  const selectedYear = yearFilter.value;

  const filtered = allPatients.filter(p => {
    const matchesSearch =
      p.first_name?.toLowerCase().includes(searchTerm) ||
      p.last_name?.toLowerCase().includes(searchTerm) ||
      p.phone?.includes(searchTerm);

    const matchesYear = selectedYear
      ? new Date(p.created_at).getFullYear().toString() === selectedYear
      : true;

    return matchesSearch && matchesYear;
  });

  displayPatients(filtered);
}

searchInput.addEventListener("input", applyFilters);
yearFilter.addEventListener("change", applyFilters);

// Initial load
fetchPatients();
