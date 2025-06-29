const token = localStorage.getItem("token");
const urlParams = new URLSearchParams(window.location.search);
const patientId = urlParams.get("patient_id");

if (!token || !patientId) {
  alert("Unauthorized access or missing patient ID.");
  window.location.href = "doctor.html";
}

const patientInfoDiv = document.getElementById("patient-info");
const resultsListDiv = document.getElementById("results-list");

// ✅ Load patient details
fetch(`http://localhost:8000/api/v1/patients/${patientId}/`, {
  headers: { Authorization: `Bearer ${token}` }
})
.then(res => res.json())
.then(patient => {
  patientInfoDiv.innerHTML = `
    <h4>${patient.first_name} ${patient.last_name}</h4>
    <p><strong>Phone:</strong> ${patient.phone}</p>
    <p><strong>Address:</strong> ${patient.address}</p>
    <p><strong>Registered on:</strong> ${new Date(patient.created_at).toLocaleString()}</p>
  `;
})
.catch(err => {
  console.error("Failed to load patient", err);
  alert("❌ Could not load patient.");
});

// ✅ Upload form
document.getElementById("upload-form").addEventListener("submit", e => {
  e.preventDefault();

  const formData = new FormData();
  formData.append("title", document.getElementById("result-title").value);
  formData.append("description", document.getElementById("result-description").value);
  formData.append("result_file", document.getElementById("result-file").files[0]);
  formData.append("patient", patientId);

  fetch("http://localhost:8000/api/v1/patient-results/", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    alert("✅ Result uploaded successfully.");
    location.reload();
  })
  .catch(err => {
    console.error("Upload failed", err);
    alert("❌ Upload failed.");
  });
});

// ✅ Load results
fetch(`http://localhost:8000/api/v1/patient-results/?patient=${patientId}`, {
  headers: { Authorization: `Bearer ${token}` }
})
.then(res => res.json())
.then(results => {
  results.forEach(result => {
    const div = document.createElement("div");
    div.innerHTML = `
      <h6>${result.title}</h6>
      <p>${result.description}</p>
      <a href="${result.result_file}" target="_blank">📎 View File</a>
      <hr/>
    `;
    resultsListDiv.appendChild(div);
  });
});
