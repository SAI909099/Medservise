document.addEventListener('DOMContentLoaded', () => {
  const urlParams = new URLSearchParams(window.location.search);
  const patientId = urlParams.get('patient_id') || 1;

  document.getElementById('patient-id').value = patientId;
  document.getElementById('patient-id-display').textContent = patientId;

  loadPatientData(patientId);

  document.getElementById('payment-form').addEventListener('submit', submitPayment);
  document.getElementById('print-all-btn').addEventListener('click', printReceipt);
});

function getCSRFToken() {
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken='))
    ?.split('=')[1];
  return cookieValue || '';
}

async function loadPatientData(patientId) {
  try {
    const token = localStorage.getItem('access_token');
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

    const response = await fetch(`http://89.39.95.150/api/v1/cash-register/patient/${patientId}/`, {
      headers: headers
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Server error: ${response.status} - ${errorText}`);
    }

    const data = await response.json();

    document.getElementById('patient-name').textContent = data.summary.patient.name;
    document.getElementById('patient-phone').textContent = data.summary.patient.phone;
    document.getElementById('total-paid').textContent = `$${data.summary.total_paid.toFixed(2)}`;
    document.getElementById('balance').textContent = `$${data.summary.balance.toFixed(2)}`;

    renderTransactions(data.transactions);
  } catch (error) {
    console.error('Error loading patient data:', error);
    alert(`Error loading patient data: ${error.message}`);
  }
}

function renderTransactions(transactions) {
  const tbody = document.getElementById('transactions-body');
  tbody.innerHTML = '';

  if (!transactions || transactions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6">No transactions found</td></tr>';
    return;
  }

  transactions.forEach(transaction => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${new Date(transaction.created_at).toLocaleString()}</td>
      <td>${transaction.transaction_type}</td>
      <td>$${parseFloat(transaction.amount).toFixed(2)}</td>
      <td>${transaction.payment_method}</td>
      <td>${transaction.notes || '-'}</td>
      <td class="actions">
        <button data-id="${transaction.id}" class="view-receipt">View</button>
        <button data-id="${transaction.id}" class="print-receipt">Print</button>
      </td>
    `;
    tbody.appendChild(row);
  });

  document.querySelectorAll('.view-receipt').forEach(btn => {
    btn.addEventListener('click', () => viewReceipt(btn.dataset.id));
  });

  document.querySelectorAll('.print-receipt').forEach(btn => {
    btn.addEventListener('click', () => printTransaction(btn.dataset.id));
  });
}

async function submitPayment(event) {
  event.preventDefault();

  const formData = {
    patient: document.getElementById('patient-id').value,
    transaction_type: document.getElementById('transaction-type').value,
    amount: document.getElementById('amount').value,
    payment_method: document.getElementById('payment-method').value,
    notes: document.getElementById('notes').value
  };

  try {
    const token = localStorage.getItem('access_token');
    const headers = {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
      'X-Requested-With': 'XMLHttpRequest'
    };

    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`http://89.39.95.150/api/v1/cash-register/`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(formData)
    });

    if (response.ok) {
      const result = await response.json();
      alert('Payment recorded successfully!');
      document.getElementById('payment-form').reset();
      loadPatientData(formData.patient);
    } else {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to record payment');
    }
  } catch (error) {
    console.error('Error recording payment:', error);
    alert(`Error recording payment: ${error.message}`);
  }
}

function viewReceipt(transactionId) {
  window.open(`http://89.39.95.150/api/v1/cash-register/receipt/${transactionId}/`, '_blank');
}

function printTransaction(transactionId) {
  console.log(`Printing receipt for transaction ${transactionId}`);
  alert(`Printing receipt for transaction ${transactionId}`);
}

function printReceipt() {
  console.log('Printing all receipts');
  alert('Printing all receipts');
}
