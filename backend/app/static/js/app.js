const state = {
  invoices: [],
  selectedInvoiceId: null,
  chart: null,
};

async function loadInvoices() {
  const response = await fetch('/api/invoices');
  if (!response.ok) {
    console.error('Failed to load invoices');
    return;
  }
  const data = await response.json();
  state.invoices = data.invoices;
  renderInvoiceList();
  if (state.invoices.length && !state.selectedInvoiceId) {
    selectInvoice(state.invoices[0].id);
  }
}

async function loadAnalytics() {
  const response = await fetch('/api/invoices/analytics/summary');
  if (!response.ok) {
    console.error('Failed to load analytics');
    return;
  }
  const data = await response.json();
  document.querySelector('#metricInvoices').textContent = data.total_invoices;
  document.querySelector('#metricTotal').textContent = formatCurrency(data.total_value, data.currency);
  document.querySelector('#metricOutstanding').textContent = formatCurrency(data.outstanding_balance, data.currency);
  renderVendorChart(data.vendors, data.currency);
}

function renderInvoiceList() {
  const list = document.querySelector('#invoiceList');
  list.innerHTML = '';
  if (!state.invoices.length) {
    const empty = document.createElement('div');
    empty.className = 'text-muted small';
    empty.textContent = 'No invoices processed yet.';
    list.appendChild(empty);
    return;
  }
  state.invoices.forEach((invoice) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = `list-group-item list-group-item-action ${state.selectedInvoiceId === invoice.id ? 'active' : ''}`;
    item.textContent = `${invoice.vendor_name || 'Unknown vendor'} • ${invoice.invoice_number || 'N/A'}`;
    item.addEventListener('click', () => selectInvoice(invoice.id));
    list.appendChild(item);
  });
}

async function selectInvoice(id) {
  state.selectedInvoiceId = id;
  renderInvoiceList();
  const response = await fetch(`/api/invoices/${id}`);
  if (!response.ok) {
    console.error('Unable to load invoice details');
    return;
  }
  const invoice = await response.json();
  updateInvoiceDetails(invoice);
  resetChatWindow();
}

function updateInvoiceDetails(invoice) {
  const detailsCard = document.querySelector('#invoiceDetails');
  detailsCard.dataset.hidden = 'false';
  const meta = [];
  if (invoice.invoice_number) meta.push(`#${invoice.invoice_number}`);
  if (invoice.invoice_date) meta.push(new Date(invoice.invoice_date).toLocaleDateString());
  if (invoice.due_date) meta.push(`Due ${new Date(invoice.due_date).toLocaleDateString()}`);

  document.querySelector('#detailVendor').textContent = invoice.vendor_name || 'Unknown vendor';
  document.querySelector('#detailInvoiceMeta').textContent = meta.join(' • ');
  document.querySelector('#detailTotal').textContent = invoice.total ? formatCurrency(invoice.total, invoice.currency) : 'Total N/A';
  document.querySelector('#detailCustomer').textContent = invoice.customer_name || invoice.customer_address || '—';
  document.querySelector('#detailTerms').textContent = invoice.payment_terms || '—';
  document.querySelector('#detailCustomerId').textContent = invoice.customer_id || '—';

  const tbody = document.querySelector('#lineItemsTable tbody');
  tbody.innerHTML = '';
  if (!invoice.line_items.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 4;
    cell.className = 'text-center text-muted';
    cell.textContent = 'No line items were detected.';
    row.appendChild(cell);
    tbody.appendChild(row);
  } else {
    invoice.line_items.forEach((item) => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${item.description || '—'}</td>
        <td class="text-end">${item.quantity ?? '—'}</td>
        <td class="text-end">${item.unit_price != null ? formatCurrency(item.unit_price, invoice.currency) : '—'}</td>
        <td class="text-end">${item.amount != null ? formatCurrency(item.amount, invoice.currency) : '—'}</td>
      `;
      tbody.appendChild(row);
    });
  }
}

function renderVendorChart(vendors, currency) {
  const ctx = document.querySelector('#vendorChart');
  const labels = Object.keys(vendors);
  const values = Object.values(vendors);
  if (state.chart) {
    state.chart.destroy();
  }
  state.chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Invoice totals',
          data: values,
          backgroundColor: 'rgba(13, 110, 253, 0.6)',
          borderColor: 'rgb(13, 110, 253)',
          borderWidth: 1,
        },
      ],
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: (value) => formatCurrency(value, currency),
          },
        },
      },
      plugins: {
        legend: {
          display: false,
        },
      },
    },
  });
}

function formatCurrency(value, currency = 'USD') {
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: currency || 'USD',
    }).format(value ?? 0);
  } catch (error) {
    return `$${Number(value || 0).toFixed(2)}`;
  }
}

function resetChatWindow() {
  const chatWindow = document.querySelector('#chatWindow');
  chatWindow.innerHTML = '';
}

async function submitChat(event) {
  event.preventDefault();
  if (!state.selectedInvoiceId) {
    return;
  }
  const input = document.querySelector('#chatInput');
  const message = input.value.trim();
  if (!message) {
    return;
  }
  appendChatMessage('user', message);
  input.value = '';
  const response = await fetch(`/api/chat/${state.selectedInvoiceId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    appendChatMessage('agent', 'I was unable to process your question.');
    return;
  }
  const data = await response.json();
  appendChatMessage('agent', data.response);
}

function appendChatMessage(role, text) {
  const chatWindow = document.querySelector('#chatWindow');
  const bubble = document.createElement('div');
  bubble.className = `message ${role}`;
  bubble.textContent = text;
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function submitUpload(event) {
  event.preventDefault();
  const fileInput = document.querySelector('#invoiceFile');
  const file = fileInput.files[0];
  if (!file) {
    return;
  }
  const spinner = document.querySelector('#uploadSpinner');
  spinner.classList.remove('d-none');
  const formData = new FormData();
  formData.append('file', file);
  try {
    const response = await fetch('/api/invoices', {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const error = await response.json();
      alert(error.detail || 'Failed to process invoice');
    } else {
      const data = await response.json();
      state.invoices.unshift(data.invoice);
      selectInvoice(data.invoice.id);
      loadAnalytics();
    }
  } finally {
    spinner.classList.add('d-none');
    event.target.reset();
  }
}

window.addEventListener('DOMContentLoaded', () => {
  loadInvoices();
  loadAnalytics();
  document.querySelector('#chatForm').addEventListener('submit', submitChat);
  document.querySelector('#uploadForm').addEventListener('submit', submitUpload);
});
