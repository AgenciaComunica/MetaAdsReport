document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((node) => {
    new bootstrap.Tooltip(node);
  });

  const loadingOverlay = document.getElementById('loadingOverlay');
  const loadingTitle = document.getElementById('loadingOverlayTitle');
  const loadingText = document.getElementById('loadingOverlayText');

  const showLoadingOverlay = (title, text) => {
    if (!loadingOverlay) {
      return;
    }
    loadingTitle.textContent = title || 'Processando';
    loadingText.textContent = text || 'Aguarde enquanto o sistema conclui esta etapa.';
    loadingOverlay.classList.add('is-visible');
    loadingOverlay.setAttribute('aria-hidden', 'false');
  };

  document.querySelectorAll('form[data-loading-title]').forEach((form) => {
    form.addEventListener('submit', () => {
      showLoadingOverlay(form.dataset.loadingTitle, form.dataset.loadingText);
    });
  });

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
