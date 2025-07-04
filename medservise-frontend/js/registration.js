document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  if (!token) {
    alert("Login required.");
    location.href = "index.html";
    return;
  }

  const headers = {
    Authorization: `Bearer ${token}`
  };

  const doctorSelect = document.getElementById("doctor_id");
  const serviceContainer = document.getElementById("service-options");
  const form = document.getElementById("patient-form");

  let allServices = [];

  // Load doctors
  fetch("http://localhost:8000/api/v1/doctor-list/", { headers })
    .then(res => res.json())
    .then(doctors => {
      doctors.forEach(doc => {
        const option = document.createElement("option");
        option.value = doc.id;
        option.textContent = `${doc.name}`;
        option.dataset.price = doc.consultation_price;
        doctorSelect.appendChild(option);
      });
    });

  // Load all services
  fetch("http://localhost:8000/api/v1/services/", { headers })
    .then(res => res.json())
    .then(data => {
      allServices = data;
    });

  doctorSelect.addEventListener("change", () => {
    const selectedDoctorId = parseInt(doctorSelect.value);
    const selectedPrice = parseFloat(doctorSelect.options[doctorSelect.selectedIndex].dataset.price || 0);
    document.getElementById("expected_fee").value = selectedPrice.toFixed(2);

    // Show services related to selected doctor
    serviceContainer.innerHTML = "";
    const filtered = allServices.filter(s => s.doctor.id === selectedDoctorId);

    filtered.forEach(service => {
      const div = document.createElement("div");
      div.className = "form-check";
      div.innerHTML = `
        <input class="form-check-input service-checkbox" type="checkbox" 
               id="service-${service.id}" value="${service.price}" data-id="${service.id}">
        <label class="form-check-label" for="service-${service.id}">
          ${service.name} ($${service.price})
        </label>
      `;
      serviceContainer.appendChild(div);
    });

    updateTotalFee();
  });

  serviceContainer.addEventListener("change", updateTotalFee);

  function updateTotalFee() {
    const doctorFee = parseFloat(document.getElementById("expected_fee").value || 0);
    const selectedServices = document.querySelectorAll(".service-checkbox:checked");
    const serviceTotal = Array.from(selectedServices).reduce((sum, el) => sum + parseFloat(el.value), 0);
    const total = doctorFee + serviceTotal;
    document.getElementById("total_fee").value = total.toFixed(2);
  }

  // Submit
  form.addEventListener("submit", (e) => {
    e.preventDefault();

    const selectedServiceIds = Array.from(document.querySelectorAll(".service-checkbox:checked"))
      .map(el => parseInt(el.dataset.id));

    const data = {
      first_name: document.getElementById("first_name").value,
      last_name: document.getElementById("last_name").value,
      age: parseInt(document.getElementById("age").value),
      phone: document.getElementById("phone").value,
      address: document.getElementById("address").value,
      doctor_id: parseInt(doctorSelect.value),
      reason: document.getElementById("reason").value,
      services: selectedServiceIds
    };

    fetch("http://localhost:8000/api/v1/register-patient/", {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
      .then(res => {
        if (!res.ok) throw new Error("Registration failed");
        return res.json();
      })
      .then(() => {
        alert("✅ Patient registered successfully");
        form.reset();
        serviceContainer.innerHTML = "";
        document.getElementById("expected_fee").value = "";
        document.getElementById("total_fee").value = "";
      })
      .catch(err => {
        console.error(err);
        alert("❌ Error: Could not register patient.");
      });
  });
});

// ✅ Logout
function logout() {
  localStorage.removeItem("token");
  window.location.href = "index.html";
}
