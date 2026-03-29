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

  const companySearchInput = document.querySelector('[data-company-search]');
  const companyCards = Array.from(document.querySelectorAll('[data-company-card]'));
  const companyEmptySearch = document.querySelector('[data-company-empty-search]');

  if (companySearchInput && companyCards.length) {
    const filterCompanies = () => {
      const term = companySearchInput.value.trim().toLowerCase();
      let visibleCount = 0;
      companyCards.forEach((card) => {
        const matches = !term || card.dataset.companyName.includes(term);
        card.classList.toggle('d-none', !matches);
        if (matches) {
          visibleCount += 1;
        }
      });
      if (companyEmptySearch) {
        companyEmptySearch.classList.toggle('d-none', visibleCount > 0);
      }
    };

    companySearchInput.addEventListener('input', filterCompanies);
    filterCompanies();
  }

  const socialLinkTemplate = document.getElementById('socialLinkRowTemplate');
  const socialLinkBuilders = document.querySelectorAll('[data-social-links]');

  const updateSocialLinksPayload = (builder) => {
    const input = document.getElementById(builder.dataset.inputId);
    if (!input) {
      return;
    }
    const payload = Array.from(builder.querySelectorAll('[data-social-link-row]')).map((row) => {
      const network = row.querySelector('[data-social-link-network]')?.value || '';
      const url = row.querySelector('[data-social-link-url]')?.value.trim() || '';
      return { network, url };
    }).filter((item) => item.network || item.url);
    input.value = JSON.stringify(payload);
  };

  const bindSocialLinkRow = (builder, row) => {
    row.querySelector('[data-social-link-network]')?.addEventListener('change', () => {
      updateSocialLinksPayload(builder);
    });
    row.querySelector('[data-social-link-url]')?.addEventListener('input', () => {
      updateSocialLinksPayload(builder);
    });
    row.querySelector('[data-social-link-remove]')?.addEventListener('click', () => {
      row.remove();
      updateSocialLinksPayload(builder);
    });
  };

  const addSocialLinkRow = (builder, initialData = {}) => {
    if (!socialLinkTemplate) {
      return;
    }
    const list = builder.querySelector('[data-social-links-list]');
    if (!list) {
      return;
    }
    const fragment = socialLinkTemplate.content.cloneNode(true);
    const row = fragment.querySelector('[data-social-link-row]');
    const networkField = fragment.querySelector('[data-social-link-network]');
    const urlField = fragment.querySelector('[data-social-link-url]');
    if (networkField) {
      networkField.value = initialData.network || '';
    }
    if (urlField) {
      urlField.value = initialData.url || '';
    }
    list.appendChild(fragment);
    bindSocialLinkRow(builder, list.lastElementChild);
    updateSocialLinksPayload(builder);
  };

  socialLinkBuilders.forEach((builder) => {
    const input = document.getElementById(builder.dataset.inputId);
    const addButton = builder.querySelector('[data-social-links-add]');
    if (!input || !addButton) {
      return;
    }

    let initialItems = [];
    if (input.value) {
      try {
        initialItems = JSON.parse(input.value);
      } catch (error) {
        initialItems = [];
      }
    }

    initialItems.forEach((item) => addSocialLinkRow(builder, item));

    addButton.addEventListener('click', () => {
      addSocialLinkRow(builder);
    });

    updateSocialLinksPayload(builder);
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
