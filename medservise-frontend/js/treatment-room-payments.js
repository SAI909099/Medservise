document.addEventListener("DOMContentLoaded", () => {
  const token = localStorage.getItem("token");
  const roomList = document.getElementById("room-list");
  let currentFilter = "all";

  // Load payment data from backend
  function loadPayments() {
    fetch("http://localhost:8000/api/v1/treatment-room-payments/", {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        roomList.innerHTML = "";

        data.forEach(room => {
          const roomDiv = document.createElement("div");
          roomDiv.classList.add("card", "mb-3", "p-3");

          // Filter patients based on currentFilter
          const filteredPatients = room.patients.filter(p => {
            if (currentFilter === "all") return true;

            if (currentFilter === "prepaid") return p.total_paid > p.expected;

            if (currentFilter === "paid") return p.total_paid >= p.expected;

            if (currentFilter === "unpaid") return p.total_paid === 0;

            return false;
          });

          let patientsHTML = "";
          filteredPatients.forEach(p => {
            const isPrepaid = p.total_paid > p.expected;
            const statusStr = isPrepaid ? "PREPAID" : (p.status ? p.status.toUpperCase() : "UNKNOWN");
            const statusColor = isPrepaid ? "text-info" :
                                p.status === "paid" ? "text-success" :
                                p.status === "partial" ? "text-warning" :
                                "text-danger";

            // Payment history, hidden by default
            let paymentHistory = "<ul class='payment-history d-none'>";
            p.payments.forEach(pay => {
              paymentHistory += `<li>${pay.amount} so'm on ${new Date(pay.date).toLocaleString()} — <i>${pay.status}</i><br>${pay.notes || ''}</li>`;
            });
            paymentHistory += "</ul>";

            patientsHTML += `
              <div class="border rounded p-2 mb-2">
                <strong>${p.first_name} ${p.last_name}</strong>
                <p>Status: <span class="${statusColor}">${statusStr}</span></p>
                <p>Paid: ${p.total_paid} so'm / ${p.expected} so'm</p>

                <button class="btn btn-outline-secondary btn-sm toggle-payment-form mb-2">▾ Add Payment</button>
                <button class="btn btn-outline-info btn-sm toggle-payment-history mb-2 ms-2">▾ Payment History</button>

                <form class="payment-form d-none" data-patient-id="${p.id}">
                  <input type="number" step="0.01" placeholder="Amount" class="form-control mb-1" required>
                  <select class="form-select mb-1" required>
                    <option value="paid">Paid</option>
                    <!-- <option value="partial">Partial</option> -->
                    <!-- <option value="unpaid">Unpaid</option> -->
                  </select>
                  <textarea class="form-control mb-1" placeholder="Notes (optional)"></textarea>
                  <button type="submit" class="btn btn-sm btn-primary">➕ Add Payment</button>
                </form>

                ${paymentHistory}
              </div>
            `;
          });

          roomDiv.innerHTML = `
            <h5>${room.name} (Floor ${room.floor})</h5>
            ${patientsHTML || "<p>No patients currently assigned for this filter.</p>"}
          `;
          roomList.appendChild(roomDiv);
        });

        attachHandlers();
      })
      .catch(err => {
        console.error("❌ Failed to load payment data", err);
        roomList.innerHTML = "<p class='text-danger'>❌ Failed to load payment data</p>";
      });
  }

  // Attach all event handlers for buttons and forms
  function attachHandlers() {
    // Toggle Add Payment form
    document.querySelectorAll(".toggle-payment-form").forEach(btn => {
      btn.addEventListener("click", () => {
        const parentDiv = btn.closest("div.border");
        if (!parentDiv) return;
        const form = parentDiv.querySelector(".payment-form");
        if (form) form.classList.toggle("d-none");
      });
    });

    // Toggle Payment History visibility
    document.querySelectorAll(".toggle-payment-history").forEach(btn => {
      btn.addEventListener("click", () => {
        const parentDiv = btn.closest("div.border");
        if (!parentDiv) return;
        const paymentHistory = parentDiv.querySelector(".payment-history");
        if (paymentHistory) paymentHistory.classList.toggle("d-none");
      });
    });

    // Handle Add Payment form submission
    document.querySelectorAll(".payment-form").forEach(form => {
      form.addEventListener("submit", e => {
        e.preventDefault();
        const patientId = form.dataset.patientId;
        const amount = parseFloat(form.querySelector("input").value);
        const status = form.querySelector("select").value;
        const notes = form.querySelector("textarea").value;

        if (!amount || amount <= 0) {
          alert("Enter a valid amount");
          return;
        }

        fetch("http://localhost:8000/api/v1/treatment-room-payments/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({ patient: patientId, amount, status, notes })
        })
          .then(res => {
            if (!res.ok) throw new Error("Failed to record payment");
            return res.json();
          })
          .then(() => {
            alert("✅ Payment added successfully");
            loadPayments();
          })
          .catch(err => {
            console.error("❌ Payment error", err);
            alert("❌ Error adding payment");
          });
      });
    });
  }

  // Filter tabs event listeners
  document.querySelectorAll("#payment-filter-tabs .nav-link").forEach(tab => {
    tab.addEventListener("click", e => {
      e.preventDefault();
      document.querySelectorAll("#payment-filter-tabs .nav-link").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      currentFilter = tab.dataset.filter;
      loadPayments(); // reload data with the new filter applied
    });
  });

  // Initial load
  loadPayments();
});
