const API_BASE = "http://127.0.0.1:5000/api";

const budgetForm = document.getElementById("budgetForm");
const expenseForm = document.getElementById("expenseForm");
const budgetInput = document.getElementById("budgetInput");
const amountInput = document.getElementById("amountInput");
const dateInput = document.getElementById("dateInput");
const categoryInput = document.getElementById("categoryInput");
const descInput = document.getElementById("descInput");
const expensesTableBody = document.getElementById("expensesTableBody");
const insightsList = document.getElementById("insightsList");
const alertBox = document.getElementById("alertBox");
const themeToggle = document.getElementById("themeToggle");

let pieChart;
let barChart;

function currency(value) {
  return `$${Number(value).toFixed(2)}`;
}

function setTheme(darkModeEnabled) {
  document.body.classList.toggle("dark", darkModeEnabled);
  localStorage.setItem("darkMode", darkModeEnabled ? "1" : "0");
}

themeToggle.addEventListener("click", () => {
  setTheme(!document.body.classList.contains("dark"));
});

async function requestJSON(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || "Request failed");
  }
  return response.json();
}

function updateStats(summary) {
  document.getElementById("budgetValue").textContent = currency(summary.monthly_budget);
  document.getElementById("expensesValue").textContent = currency(summary.total_expenses);
  document.getElementById("remainingValue").textContent = currency(summary.remaining_budget);
  document.getElementById("plValue").textContent = currency(summary.profit_or_loss);

  const remainingElement = document.getElementById("remainingValue");
  remainingElement.style.color = summary.remaining_budget < 0 ? "#dc2626" : "#16a34a";
}

function renderInsights(summary) {
  insightsList.innerHTML = "";
  (summary.insights || []).forEach((text) => {
    const li = document.createElement("li");
    li.textContent = text;
    insightsList.appendChild(li);
  });

  if (summary.alert) {
    alertBox.textContent = summary.alert;
    alertBox.classList.remove("hidden");
  } else {
    alertBox.classList.add("hidden");
  }
}

function renderExpenses(expenses) {
  expensesTableBody.innerHTML = "";
  expenses.forEach((expense) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${expense.date}</td>
      <td>${expense.category}</td>
      <td>${expense.description || "-"}</td>
      <td>${currency(expense.amount)}</td>
      <td><button class="danger" data-id="${expense.id}">Delete</button></td>
    `;
    expensesTableBody.appendChild(tr);
  });
}

function drawCharts(summary) {
  const categoryLabels = summary.category_totals.map((x) => x.category);
  const categoryData = summary.category_totals.map((x) => x.total);

  const weekLabels = summary.weekly_totals.map((x) => x.label);
  const weekData = summary.weekly_totals.map((x) => x.total);

  if (pieChart) pieChart.destroy();
  if (barChart) barChart.destroy();

  pieChart = new Chart(document.getElementById("categoryPie"), {
    type: "pie",
    data: {
      labels: categoryLabels.length ? categoryLabels : ["No data"],
      datasets: [
        {
          data: categoryData.length ? categoryData : [1],
          backgroundColor: ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0ea5e9"],
        },
      ],
    },
  });

  barChart = new Chart(document.getElementById("weeklyBar"), {
    type: "bar",
    data: {
      labels: weekLabels,
      datasets: [
        {
          label: "Weekly Spending",
          data: weekData,
          backgroundColor: "#2563eb",
        },
      ],
    },
    options: {
      scales: {
        y: {
          beginAtZero: true,
        },
      },
    },
  });
}

async function loadData() {
  const [budget, expenses, summary] = await Promise.all([
    requestJSON(`${API_BASE}/budget`),
    requestJSON(`${API_BASE}/expenses`),
    requestJSON(`${API_BASE}/summary`),
  ]);

  budgetInput.value = budget.monthly_budget;
  updateStats(summary);
  renderExpenses(expenses);
  renderInsights(summary);
  drawCharts(summary);
}

budgetForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await requestJSON(`${API_BASE}/budget`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ monthly_budget: Number(budgetInput.value) }),
    });
    await loadData();
  } catch (error) {
    alert(error.message);
  }
});

expenseForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await requestJSON(`${API_BASE}/expenses`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount: Number(amountInput.value),
        date: dateInput.value,
        category: categoryInput.value,
        description: descInput.value,
      }),
    });
    expenseForm.reset();
    dateInput.valueAsDate = new Date();
    await loadData();
  } catch (error) {
    alert(error.message);
  }
});

expensesTableBody.addEventListener("click", async (event) => {
  const target = event.target;
  if (!target.classList.contains("danger")) return;
  const id = target.getAttribute("data-id");
  if (!confirm("Delete this expense?")) return;
  await fetch(`${API_BASE}/expenses/${id}`, { method: "DELETE" });
  await loadData();
});

function boot() {
  dateInput.valueAsDate = new Date();
  setTheme(localStorage.getItem("darkMode") === "1");
  loadData().catch((error) => {
    alert(`Failed to load app data: ${error.message}`);
  });
}

boot();
