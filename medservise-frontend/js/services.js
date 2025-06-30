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

  // 🔄 Load doctors into dropdown
  function loadDoctors() {
    fetch("http://localhost:8000/api/v1/doctor-list/", {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    })
      .then(res => res.json())
      .then(doctors => {
        doctorSelect.innerHTML = '<option disabled selected>Select Doctor</option>';
        doctors.forEach(doc => {
          const opt = document.createElement("option");
          opt.value = doc.id;
          opt.textContent = `${doc.name} (${doc.specialty})`;
          doctorSelect.appendChild(opt);
        });
      });
  }

  // 🔄 Load existing services
  function loadServices() {
    fetch("http://localhost:8000/api/v1/services/", {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    })
      .then(res => res.json())
      .then(services => {
        serviceList.innerHTML = "";
        services.forEach(service => {
          const li = document.createElement("li");
          li.className = "list-group-item d-flex justify-content-between align-items-center";
          li.textContent = `${service.name} - $${service.price} (Dr. ${service.doctor?.name || "Unknown"})`;
          serviceList.appendChild(li);
        });
      });
  }

  loadDoctors();
  loadServices();

  // 🩺 Register new doctor
  doctorForm.addEventListener("submit", e => {
    e.preventDefault();

    const name = document.getElementById("doctor-name").value.trim();
    const email = document.getElementById("doctor-email").value.trim();
    const password = document.getElementById("doctor-password").value;
    const specialty = document.getElementById("doctor-specialty").value.trim();

    // First create User account
    fetch("http://localhost:8000/api/v1/register/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        first_name: name,
        last_name: "Doctor",
        email,
        password,
        confirm_password: password,
        date_of_birth: "1980-01-01",
        phone_number: "0000000000"
      })
    })
      .then(res => {
        if (!res.ok) throw new Error("❌ Failed to register doctor account");
        return res.json();
      })
      .then(() => {
        // Then create doctor profile
        return fetch("http://localhost:8000/api/v1/doctor-list/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({ name, specialty })
        });
      })
      .then(res => {
        if (!res.ok) throw new Error("❌ Failed to create doctor profile");
        return res.json();
      })
      .then(() => {
        doctorForm.reset();
        loadDoctors();
        alert("✅ Doctor registered and added successfully");
      })
      .catch(err => {
        alert(err.message || "❌ Could not register doctor");
        console.error(err);
      });
  });

  // ➕ Create a new service
  serviceForm.addEventListener("submit", e => {
    e.preventDefault();

    const name = document.getElementById("service-name").value.trim();
    const price = parseFloat(document.getElementById("service-price").value);
    const doctor_id = parseInt(document.getElementById("doctor-select").value);

    fetch("http://localhost:8000/api/v1/services/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`  // ✅ Secure service creation
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
});
