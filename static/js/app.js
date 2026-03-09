document.addEventListener('DOMContentLoaded', () => {
  const chart = document.getElementById('timelineChart');
  if (!chart) {
    return;
  }

  const parseDataset = (value) => {
    if (!value) {
      return [];
    }
    try {
      return JSON.parse(value);
    } catch (error) {
      return JSON.parse(value.replace(/'/g, '"'));
    }
  };

  const labels = parseDataset(chart.dataset.labels);
  const values = parseDataset(chart.dataset.values);

  new Chart(chart, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Investimento',
        data: values,
        tension: 0.35,
        borderColor: '#cb5f2c',
        backgroundColor: 'rgba(203, 95, 44, 0.15)',
        fill: true,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });
  chart.style.minHeight = '320px';
});
