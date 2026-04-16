<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ $report_title }}</title>
    <style>
        {!! file_get_contents(public_path('css/app.css')) !!}
        body { background:#f8f5ef; padding:24px; }
        .report-shell { max-width: 1440px; margin:0 auto; }
        .report-topbar { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:24px; }
        .report-meta { color:#6b7280; font-size:14px; }
        .report-tabs { display:flex; flex-wrap:wrap; gap:8px; border-bottom:1px solid #e5d8c2; padding-bottom:12px; margin-bottom:20px; }
        .report-tab-button { border:1px solid #e5d8c2; background:#fff; border-radius:14px 14px 0 0; padding:10px 18px; font-weight:700; cursor:pointer; }
        .report-tab-button.active { background:#f6ede2; color:#9a5520; }
        .report-pane { display:none; }
        .report-pane.active { display:block; }
        .report-chart { min-height:320px; }
        .report-muted { color:#6b7280; }
        .report-section + .report-section { margin-top:24px; }
    </style>
</head>
<body>
    <div class="report-shell">
        <div class="report-topbar">
            <div>
                <h1 class="page-title mb-1">{{ $report_title }}</h1>
                <div class="report-meta">
                    <div>Empresa: {{ $empresa->nome }}</div>
                    <div>Período atual: {{ $periodo_atual_resumo }}</div>
                    <div>Período anterior: {{ $periodo_anterior_resumo }}</div>
                </div>
            </div>
            <div class="report-meta text-end">
                <div>Gerado em {{ $generated_at->format('d/m/Y H:i') }}</div>
                <div>Snapshot offline do dashboard</div>
            </div>
        </div>

        <div class="panel">
            <div class="report-tabs" role="tablist">
                @foreach ($report_tabs as $index => $tab)
                    <button type="button" class="report-tab-button {{ $index === 0 ? 'active' : '' }}" data-report-tab="{{ $tab['key'] }}">
                        {{ $tab['title'] }}
                    </button>
                @endforeach
            </div>

            @foreach ($report_tabs as $index => $tab)
                @php
                    $content = $tab['content'];
                @endphp
                <section class="report-pane {{ $index === 0 ? 'active' : '' }}" data-report-pane="{{ $tab['key'] }}">
                    @if ($tab['panel_type'] === 'trafego_pago' && $content)
                        <div class="dashboard-tab-header">
                            <div>
                                <h3 class="mb-1">{{ $content['title'] }}</h3>
                                <p class="report-muted mb-0">{{ $content['description'] }}</p>
                            </div>
                        </div>

                        @if (! empty($content['tab_chart']))
                            <div class="panel mt-4 report-section">
                                <h3 class="mb-1">Evolução Mensal</h3>
                                <div id="report-chart-{{ $tab['key'] }}" class="report-chart mt-3"></div>
                                <script type="application/json" id="report-chart-data-{{ $tab['key'] }}">@json($content['tab_chart'])</script>
                            </div>
                        @endif

                        <div class="row g-4 mt-1 report-section">
                            @foreach ($content['metric_blocks'] as $block)
                                <div class="col-lg-6">
                                    <div class="panel traffic-block-panel {{ ! empty($block['highlighted']) ? 'is-results' : '' }}">
                                        <h3 class="mb-1">{{ $block['title'] }}</h3>
                                        <p class="report-muted mb-0">{{ $block['description'] }}</p>
                                        <div class="table-responsive mt-3">
                                            <table class="table align-middle traffic-summary-table mb-0">
                                                <thead><tr><th>Métrica</th><th>Valor</th><th>Variação</th></tr></thead>
                                                <tbody>
                                                @foreach ($block['rows'] as $row)
                                                    <tr>
                                                        <td>{{ $row['label'] }}</td>
                                                        <td><strong>{{ $row['current_value'] }}</strong></td>
                                                        <td class="{{ $row['variation_class'] }}">{{ $row['variation_value'] }}</td>
                                                    </tr>
                                                @endforeach
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            @endforeach
                        </div>

                        <div class="panel mt-4 report-section">
                            <h3>Tabela por campanha</h3>
                            <div class="table-responsive">
                                <table class="table align-middle">
                                    <thead><tr><th>Campanha</th><th>Investimento</th><th>Impressões</th><th>Alcance</th><th>Cliques</th><th>CTR</th><th>CPC</th><th>CPM</th><th>Resultados</th><th>CPL</th></tr></thead>
                                    <tbody>
                                    @forelse ($tab['campaign_rows'] as $row)
                                        <tr>
                                            <td>{{ $row['campanha'] }}</td>
                                            <td>{{ br_currency($row['investimento']) }}</td>
                                            <td>{{ br_number($row['impressoes'], 0) }}</td>
                                            <td>{{ br_number($row['alcance'], 0) }}</td>
                                            <td>{{ br_number($row['cliques'], 0) }}</td>
                                            <td>{{ br_number($row['ctr'], 2) }}%</td>
                                            <td>{{ br_currency($row['cpc']) }}</td>
                                            <td>{{ br_currency($row['cpm']) }}</td>
                                            <td>{{ br_number($row['resultados'], 2) }}</td>
                                            <td>{{ br_currency($row['cpl']) }}</td>
                                        </tr>
                                    @empty
                                        <tr><td colspan="10">Nenhum dado para o período selecionado.</td></tr>
                                    @endforelse
                                    </tbody>
                                </table>
                            </div>
                        </div>

                    @elseif ($tab['panel_type'] === 'crm_vendas' && $content)
                        <div class="dashboard-tab-header">
                            <div>
                                <h3 class="mb-1">{{ $content['title'] }}</h3>
                                <p class="report-muted mb-0">{{ $content['description'] }}</p>
                            </div>
                        </div>

                        @if (! empty($content['tab_chart']))
                            <div class="panel mt-4 report-section">
                                <h3 class="mb-1">Evolução Mensal</h3>
                                <div id="report-chart-{{ $tab['key'] }}" class="report-chart mt-3"></div>
                                <script type="application/json" id="report-chart-data-{{ $tab['key'] }}">@json($content['tab_chart'])</script>
                            </div>
                        @endif

                        <div class="row g-4 mt-1 report-section">
                            @foreach ($content['category_blocks'] as $block)
                                <div class="{{ ($block['key'] ?? '') === 'vendedor' || ($block['chart_type'] ?? '') === 'pie' ? 'col-12' : 'col-lg-6' }}">
                                    <div class="panel traffic-block-panel">
                                        <h3 class="mb-1">{{ $block['title'] }}</h3>
                                        <p class="report-muted mb-0">{{ $block['description'] }}</p>
                                        @if (! empty($block['chart']))
                                            <div id="report-chart-{{ $tab['key'] }}-{{ $block['key'] }}" class="report-chart mt-3"></div>
                                            <script type="application/json" id="report-chart-data-{{ $tab['key'] }}-{{ $block['key'] }}">@json($block['chart'])</script>
                                            <script type="application/json" id="report-chart-meta-{{ $tab['key'] }}-{{ $block['key'] }}">@json(['type' => $block['chart_type'] ?? 'line'])</script>
                                        @endif
                                        @if (! empty($block['rows']))
                                            <div class="table-responsive mt-3">
                                                <table class="table align-middle traffic-summary-table mb-0">
                                                    <thead><tr><th>Métrica</th><th>Valor</th><th>Variação</th></tr></thead>
                                                    <tbody>
                                                    @foreach ($block['rows'] as $row)
                                                        <tr>
                                                            <td @if(! empty($row['label_color'])) style="color: {{ $row['label_color'] }}; font-weight:700;" @endif>{{ $row['label'] }}</td>
                                                            <td><strong>{{ $row['current_value'] }}</strong></td>
                                                            <td class="{{ $row['variation_class'] }}">{{ $row['variation_value'] }}</td>
                                                        </tr>
                                                    @endforeach
                                                    </tbody>
                                                </table>
                                            </div>
                                        @endif
                                    </div>
                                </div>
                            @endforeach
                        </div>

                    @elseif ($tab['panel_type'] === 'redes_sociais' && $content)
                        <div class="dashboard-tab-header">
                            <div>
                                <h3 class="mb-1">{{ $content['title'] }}</h3>
                                <p class="report-muted mb-0">{{ $content['description'] }}</p>
                            </div>
                        </div>

                        @if (! empty($content['tab_chart']))
                            <div class="panel mt-4 report-section">
                                <h3 class="mb-1">Evolução Mensal</h3>
                                <div id="report-chart-{{ $tab['key'] }}" class="report-chart mt-3"></div>
                                <script type="application/json" id="report-chart-data-{{ $tab['key'] }}">@json($content['tab_chart'])</script>
                            </div>
                        @endif

                        <div class="row g-4 mt-1 report-section">
                            @foreach ($content['category_blocks'] as $block)
                                <div class="col-lg-6">
                                    <div class="panel traffic-block-panel">
                                        <h3 class="mb-1">{{ $block['title'] }}</h3>
                                        <p class="report-muted mb-0">{{ $block['description'] }}</p>
                                        <div class="table-responsive mt-3">
                                            <table class="table align-middle traffic-summary-table mb-0">
                                                <thead><tr><th>Métrica</th><th>Valor</th><th>Variação</th></tr></thead>
                                                <tbody>
                                                @foreach ($block['rows'] as $row)
                                                    <tr>
                                                        <td>{{ $row['label'] }}</td>
                                                        <td><strong>{{ $row['current_value'] }}</strong></td>
                                                        <td class="{{ $row['variation_class'] }}">{{ $row['variation_value'] }}</td>
                                                    </tr>
                                                @endforeach
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            @endforeach
                        </div>

                    @elseif ($tab['panel_type'] === 'leads_eventos' && $content)
                        <div class="dashboard-tab-header">
                            <div>
                                <h3 class="mb-1">{{ $content['title'] }}</h3>
                                <p class="report-muted mb-0">{{ $content['description'] }}</p>
                            </div>
                        </div>

                        @if (! empty($content['tab_chart']))
                            <div class="panel mt-4 report-section">
                                <h3 class="mb-1">Evolução Mensal — Pessoas Alcançadas</h3>
                                <div id="report-chart-{{ $tab['key'] }}" class="report-chart mt-3"></div>
                                <script type="application/json" id="report-chart-data-{{ $tab['key'] }}">@json($content['tab_chart'])</script>
                            </div>
                        @endif

                        <div class="panel mt-4 report-section">
                            <h3>Lista de Eventos</h3>
                            <div class="table-responsive">
                                <table class="table align-middle">
                                    <thead><tr><th>Evento</th><th>Data</th><th>Impacto</th><th>Pessoas alcançadas</th></tr></thead>
                                    <tbody>
                                    @forelse ($content['rows'] as $row)
                                        <tr>
                                            <td>{{ $row['evento'] }}</td>
                                            <td>{{ br_date($row['data_evento']) }}</td>
                                            <td>{{ $row['impacto'] }}</td>
                                            <td>{{ br_number($row['leads_media'], 0) }}</td>
                                        </tr>
                                    @empty
                                        <tr><td colspan="4">Sem dados disponíveis.</td></tr>
                                    @endforelse
                                    </tbody>
                                </table>
                            </div>
                        </div>

                    @elseif ($tab['panel_type'] === 'analise_completa' && $content)
                        <div class="dashboard-tab-header">
                            <div>
                                <h3 class="mb-1">Resumo Executivo</h3>
                                <p class="report-muted mb-0">{{ $content['description'] }}</p>
                            </div>
                        </div>

                        @if (! empty($content['tab_chart']))
                            <div class="panel mt-4 report-section">
                                <h3 class="mb-1">Evolução Mensal — Visão Geral</h3>
                                <div id="report-chart-{{ $tab['key'] }}" class="report-chart mt-3"></div>
                                <script type="application/json" id="report-chart-data-{{ $tab['key'] }}">@json($content['tab_chart'])</script>
                            </div>
                        @endif

                        <div class="row g-3 mt-1 report-section">
                            @foreach ($content['top_cards'] as $item)
                                <div class="col-md-6 col-xl-3">
                                    <div class="kpi-card h-100">
                                        <span class="kpi-label">{{ $item['label'] }}</span>
                                        <strong>{{ $item['value'] }}</strong>
                                    </div>
                                </div>
                            @endforeach
                        </div>

                        <div class="row g-4 mt-1 report-section">
                            @foreach ($content['summary_panels'] as $panel)
                                <div class="col-lg-6">
                                    <div class="panel traffic-block-panel h-100">
                                        <h3 class="mb-1">{{ $panel['title'] }}</h3>
                                        <p class="report-muted mb-0">{{ $panel['description'] }}</p>
                                        <div class="table-responsive mt-3">
                                            <table class="table align-middle traffic-summary-table mb-0">
                                                <thead><tr><th>Métrica</th><th>Valor</th><th>Variação</th></tr></thead>
                                                <tbody>
                                                @foreach ($panel['rows'] as $row)
                                                    <tr>
                                                        <td>{{ $row['label'] }}</td>
                                                        <td><strong>{{ $row['current_value'] }}</strong></td>
                                                        <td class="{{ $row['variation_class'] }}">{{ $row['variation_value'] }}</td>
                                                    </tr>
                                                @endforeach
                                                </tbody>
                                            </table>
                                        </div>
                                    </div>
                                </div>
                            @endforeach
                        </div>

                        <div class="panel mt-4 report-section">
                            <h3>Sinais dos Concorrentes</h3>
                            <div class="table-responsive">
                                <table class="table align-middle mb-0">
                                    <thead><tr><th>Concorrente</th><th>Atividade</th><th>Ads observados</th><th>Cadência</th></tr></thead>
                                    <tbody>
                                    @forelse ($content['competitor_signals'] as $item)
                                        <tr>
                                            <td>{{ $item['nome'] }}</td>
                                            <td>{{ $item['atividade'] }}</td>
                                            <td>{{ $item['ads_count'] }}</td>
                                            <td>{{ $item['cadencia'] }}</td>
                                        </tr>
                                    @empty
                                        <tr><td colspan="4">Nenhum concorrente com sinais disponíveis.</td></tr>
                                    @endforelse
                                    </tbody>
                                </table>
                            </div>
                        </div>

                    @elseif ($tab['panel_type'] === 'concorrentes' && $content)
                        <div class="dashboard-tab-header">
                            <div>
                                <h3 class="mb-1">Concorrentes</h3>
                                <p class="report-muted mb-0">Base observável/importada de anúncios públicos dos concorrentes.</p>
                            </div>
                        </div>

                        <div class="panel mt-4 report-section">
                            <h3>Lista de Concorrentes</h3>
                            <div class="table-responsive">
                                <table class="table align-middle">
                                    <thead><tr><th>Concorrente</th><th>Score</th><th>Última avaliação</th><th>Plataforma</th></tr></thead>
                                    <tbody>
                                    @forelse ($content['concorrentes_list'] as $ad)
                                        <tr>
                                            <td>{{ $ad['concorrente_nome'] }}</td>
                                            <td>{{ $ad['score_digital_label'] }}</td>
                                            <td>{{ $ad['data_referencia'] ? br_date($ad['data_referencia']) : br_datetime($ad['created_at']) }}</td>
                                            <td>{{ $ad['plataforma'] }}</td>
                                        </tr>
                                    @empty
                                        <tr><td colspan="4">Nenhum anúncio concorrente cadastrado.</td></tr>
                                    @endforelse
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    @endif
                </section>
            @endforeach
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <script>
        document.querySelectorAll('.report-tab-button').forEach((button) => {
            button.addEventListener('click', () => {
                const key = button.getAttribute('data-report-tab');
                document.querySelectorAll('.report-tab-button').forEach((item) => item.classList.toggle('active', item === button));
                document.querySelectorAll('.report-pane').forEach((pane) => pane.classList.toggle('active', pane.getAttribute('data-report-pane') === key));
                window.dispatchEvent(new Event('resize'));
            });
        });

        const formatNumberBr = (value, decimals = 2) => {
            const number = Number(value ?? 0);
            if (Number.isNaN(number)) return value;
            return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: decimals }).format(number);
        };

        const renderChart = (nodeId, chart, chartType = 'line') => {
            const node = document.getElementById(nodeId);
            if (!node || !chart) return;
            if (chartType === 'pie') {
                new ApexCharts(node, {
                    chart: { type: 'pie', height: 420, toolbar: { show: false } },
                    colors: chart.colors || ['#175cd3', '#2d6a4f', '#c67a1a', '#7c3aed', '#dc2626', '#0f766e'],
                    series: chart.series || [],
                    labels: chart.labels || [],
                    legend: { show: true, position: 'bottom' }
                }).render();
                return;
            }

            const apexType = chartType === 'mixed_area' ? 'line' : chartType;
            new ApexCharts(node, {
                chart: { type: apexType, height: 360, toolbar: { show: false }, zoom: { enabled: false } },
                colors: chart.colors || ['#175cd3', '#2d6a4f', '#c67a1a', '#7c3aed', '#dc2626', '#0f766e'],
                series: chart.series || [],
                xaxis: { categories: chart.categories || [], labels: { style: { fontSize: '11px' } } },
                yaxis: { labels: { formatter(value) { return formatNumberBr(value, 2); } } },
                stroke: { curve: 'smooth', width: (chart.series || []).map((item) => item.type === 'line' ? 3 : 2) },
                dataLabels: { enabled: true, formatter(value) { return formatNumberBr(value, 0); }, style: { fontSize: '10px', fontWeight: '600' }, background: { enabled: true, borderRadius: 3, padding: 2, opacity: 0.85 }, offsetY: -6 },
                legend: { position: 'bottom' },
                tooltip: { shared: true, y: { formatter(value) { return formatNumberBr(value, 2); } } }
            }).render();
        };

        document.querySelectorAll('script[id^="report-chart-data-"]').forEach((scriptNode) => {
            const suffix = scriptNode.id.replace('report-chart-data-', '');
            const chart = JSON.parse(scriptNode.textContent);
            const metaNode = document.getElementById(`report-chart-meta-${suffix}`);
            const chartType = metaNode ? (JSON.parse(metaNode.textContent).type || 'line') : (chart.chart_type || 'line');
            renderChart(`report-chart-${suffix}`, chart, chartType);
        });
    </script>
</body>
</html>
