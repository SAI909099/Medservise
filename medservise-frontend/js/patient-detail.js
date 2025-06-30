const token = localStorage.getItem("token");
const urlParams = new URLSearchParams(window.location.search);
const patientId = urlParams.get("patient_id");

if (!token || !patientId) {
  alert("Unauthorized access or missing patient ID.");
  window.location.href = "doctor.html";
}

const patientInfoDiv = document.getElementById("patient-info");
const resultsListDiv = document.getElementById("results-list");

// ✅ Load patient info
fetch(`http://localhost:8000/api/v1/patients/${patientId}/`, {
  headers: { Authorization: `Bearer ${token}` }
})
  .then(res => res.json())
  .then(patient => {
    patientInfoDiv.innerHTML = `
      <h4>${patient.first_name ?? "?"} ${patient.last_name ?? "?"}</h4>
      <p><strong>Phone:</strong> ${patient.phone ?? "?"}</p>
      <p><strong>Address:</strong> ${patient.address ?? "?"}</p>
      <p><strong>Registered on:</strong> ${new Date(patient.created_at).toLocaleString()}</p>
    `;
  })
  .catch(err => {
    console.error("❌ Patient load failed", err);
    alert("❌ Could not load patient info");
  });

// ✅ Upload result
document.getElementById("upload-form").addEventListener("submit", e => {
  e.preventDefault();

  const title = document.getElementById("result-title").value.trim();
  const file = document.getElementById("result-file").files[0];
  const desc = document.getElementById("result-description").value;

  if (!title || !file) {
    alert("❌ Title and file are required.");
    return;
  }

  const formData = new FormData();
  formData.append("title", title);
  formData.append("description", desc);
  formData.append("result_file", file);
  formData.append("patient", patientId);

  fetch("http://localhost:8000/api/v1/patient-results/", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: formData
  })
    .then(async res => {
      if (!res.ok) {
        const errText = await res.text();
        console.error("❌ Server error:", errText);
        throw new Error("Upload failed");
      }
      return res.json();
    })
    .then(() => {
      alert("✅ Result uploaded successfully.");
      loadResults();
    })
    .catch(err => {
      console.error("Upload failed", err);
      alert("❌ Upload failed. Please check file and title.");
    });
});

// ✅ Load all results for the specific patient
function loadResults() {
  resultsListDiv.innerHTML = "<p>Loading...</p>";

  fetch(`http://localhost:8000/api/v1/patient-results/?patient=${patientId}`, {
    headers: { Authorization: `Bearer ${token}` }
  })
    .then(res => res.json())
    .then(results => {
      if (!results.length) {
        resultsListDiv.innerHTML = "<p>No uploaded results found.</p>";
        return;
      }

      resultsListDiv.innerHTML = "";
      results.forEach(result => {
        const div = document.createElement("div");
        div.className = "border p-2 mb-3";
        div.innerHTML = `
          <h6>${result.title}</h6>
          <p>${result.description ?? "No description"}</p>
          <a href="${result.result_file}" target="_blank" class="btn btn-sm btn-outline-primary me-2">
            📄 View Info
          </a>
          <button onclick="deleteResult(${result.id})" class="btn btn-sm btn-outline-danger mt-2">
            🗑 Delete
          </button><br>
          <small>🕒 ${new Date(result.uploaded_at).toLocaleString()}</small>
        `;
        resultsListDiv.appendChild(div);
      });
    })
    .catch(err => {
      console.error("❌ Fetch failed", err);
      resultsListDiv.innerHTML = "<p>❌ Failed to load results.</p>";
    });
}

// ✅ Delete
function deleteResult(id) {
  if (!confirm("Delete this result?")) return;

  fetch(`http://localhost:8000/api/v1/patient-results/${id}/`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
    .then(res => {
      if (!res.ok) throw new Error("Delete failed");
      alert("🗑️ Deleted");
      loadResults();
    })
    .catch(err => {
      console.error("Delete error", err);
      alert("❌ Could not delete");
    });
}

// ✅ Initial load
loadResults();
