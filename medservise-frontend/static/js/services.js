document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("Please log in first.");
    window.location.href = "index.html";
    return;
  }

  const doctorForm = document.getElementById("doctor-register-form");
  const serviceForm = document.getElementById("service-form");
  const doctorSelect = document.getElementById("doctor-select");
  const serviceList = document.getElementById("service-list");
  const doctorList = document.getElementById("doctor-list");

  function loadDoctors() {
    fetch("http://localhost:8000/api/v1/doctor-list/", {
      headers: { "Authorization": `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(doctors => {
        // Populate dropdown
        if (doctorSelect) {
          doctorSelect.innerHTML = '<option disabled selected>Select Doctor</option>';
          doctors.forEach(doc => {
            const opt = document.createElement("option");
            opt.value = doc.id;
            opt.textContent = `${doc.name} (${doc.specialty})`;
            doctorSelect.appendChild(opt);
          });
        }

        // Populate doctor list
        if (doctorList) {
          doctorList.innerHTML = "";
          doctors.forEach(doc => {
            const li = document.createElement("li");
            li.className = "list-group-item d-flex justify-content-between align-items-center";
            li.innerHTML = `
              <div>
                <strong>${doc.name}</strong> | ${doc.specialty} | ${doc.consultation_price || 0} so'm
              </div>
              <div>
                <button class="btn btn-sm btn-warning me-2" onclick="editDoctor(${doc.id})">Edit</button>
                <button class="btn btn-sm btn-danger" onclick="deleteDoctor(${doc.id})">Delete</button>
              </div>
            `;
            doctorList.appendChild(li);
          });
        }
      });
  }

  function loadServices() {
    fetch("http://localhost:8000/api/v1/services/", {
      headers: { "Authorization": `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(services => {
        if (serviceList) {
          serviceList.innerHTML = "";
          services.forEach(service => {
            const li = document.createElement("li");
            li.className = "list-group-item d-flex justify-content-between align-items-center";
            li.textContent = `${service.name} - ${service.price} so'm (Dr. ${service.doctor?.name || "Unknown"})`;
            serviceList.appendChild(li);
          });
        }
      });
  }

  // Initial load
  loadDoctors();
  loadServices();

  // Doctor Registration (only if form exists)
  if (doctorForm) {
    doctorForm.addEventListener("submit", e => {
      e.preventDefault();

      const name = document.getElementById("doctor-name").value.trim();
      const email = document.getElementById("doctor-email").value.trim();
      const password = document.getElementById("doctor-password").value;
      const specialty = document.getElementById("doctor-specialty").value.trim();
      const consultation_price = parseFloat(document.getElementById("doctor-price").value);

      fetch("http://localhost:8000/api/v1/doctor-register/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          name,
          email,
          password,
          specialty,
          consultation_price
        })
      })
        .then(res => {
          if (!res.ok) throw new Error("❌ Failed to register doctor");
          return res.json();
        })
        .then(() => {
          doctorForm.reset();
          loadDoctors();
          alert("✅ Doctor registered successfully");
        })
        .catch(err => {
          alert(err.message || "❌ Could not register doctor");
          console.error(err);
        });
    });
  }

  // Service Creation (always active)
  if (serviceForm) {
    serviceForm.addEventListener("submit", e => {
      e.preventDefault();

      const name = document.getElementById("service-name").value.trim();
      const price = parseFloat(document.getElementById("service-price").value);
      const doctor_id = parseInt(document.getElementById("doctor-select").value);

      fetch("http://localhost:8000/api/v1/services/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ name, price, doctor_id })
      })
        .then(res => {
          if (!res.ok) throw new Error("❌ Failed to create service");
          return res.json();
        })
        .then(() => {
          serviceForm.reset();
          loadServices();
          alert("✅ Service added successfully");
        })
        .catch(err => {
          alert(err.message || "❌ Could not create service");
          console.error(err);
        });
    });
  }

  // Global edit/delete doctor actions (used by buttons)
  window.editDoctor = (id) => {
    const newPrice = prompt("Enter new consultation price:");
    if (!newPrice) return;

    fetch(`http://localhost:8000/api/v1/doctor-list/${id}/`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ consultation_price: parseFloat(newPrice) })
    })
      .then(res => {
        if (!res.ok) throw new Error("Failed to update doctor");
        return res.json();
      })
      .then(() => {
        loadDoctors();
        alert("✅ Doctor updated");
      })
      .catch(console.error);
  };

  window.deleteDoctor = (id) => {
    if (!confirm("Are you sure you want to delete this doctor?")) return;

    fetch(`http://localhost:8000/api/v1/doctor-list/${id}/`, {
      method: "DELETE",
      headers: {
        "Authorization": `Bearer ${token}`
      }
    })
      .then(res => {
        if (res.ok) {
          loadDoctors();
          alert("🗑️ Doctor deleted");
        } else {
          throw new Error("Delete failed");
        }
      })
      .catch(console.error);
  };
});
