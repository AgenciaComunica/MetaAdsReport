@extends('layouts.app')

@section('page_title', 'Dashboard')

@section('page_actions')
    @if ($empresa)
        <a href="{{ route('empresas.panels', $empresa->id) }}" class="btn btn-outline-dark">Configurar Painéis</a>
    @endif
@endsection

@section('content')
<style>
.panel-collapse-btn{color:#94a3b8;background:none;border:none;padding:2px 4px;line-height:1;flex-shrink:0;transition:color .15s}
.panel-collapse-btn:hover{color:#334155}
.panel-collapse-btn svg{display:block;transition:transform .2s ease}
.panel-collapse-btn[aria-expanded="false"] svg{transform:rotate(-180deg)}
</style>

<div class="panel mt-4 form-panel">
    <div class="d-flex align-items-center gap-3 flex-wrap">
        <form method="get" id="monthSelectorForm" class="d-flex align-items-center gap-2 flex-wrap">
            <input type="hidden" name="tab" value="{{ $dashboard_tab }}">
            <label for="monthSelect" class="form-label mb-0 fw-semibold text-nowrap">Mês</label>
            <select id="monthSelect" name="mes" class="form-select form-select-sm" style="width:auto;" onchange="this.form.submit()">
                @foreach ($available_months as $month)
                    <option value="{{ $month['value'] }}" @selected($month['value'] === $selected_month)>{{ $month['label'] }}</option>
                @endforeach
            </select>
            <label for="yearSelect" class="form-label mb-0 fw-semibold text-nowrap">Ano</label>
            <select id="yearSelect" name="ano" class="form-select form-select-sm" style="width:auto;" onchange="this.form.submit()">
                @foreach ($available_years as $year)
                    <option value="{{ $year }}" @selected($year === $selected_year)>{{ $year }}</option>
                @endforeach
            </select>
        </form>
        <span class="text-muted small">Comparando com {{ $periodo_anterior_resumo }}</span>
    </div>
</div>

<div class="panel mt-4">
    <ul class="nav nav-tabs dashboard-data-tabs" role="tablist">
        @foreach ($visible_dashboard_tabs as $tab)
            <li class="nav-item" role="presentation">
                <a href="{{ route('campanhas.dashboard', ['tab' => $tab['key'], 'mes' => $selected_month, 'ano' => $selected_year]) }}" class="nav-link {{ $dashboard_tab === $tab['key'] ? 'active' : '' }}">
                    {{ $tab['title'] }}
                </a>
            </li>
        @endforeach
    </ul>

    <div class="pt-4">
        @if ($active_upload_tab && $active_upload_tab['panel_type'] === 'trafego_pago')
            <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                <div>
                    <h3 class="mb-1">{{ $active_upload_tab['title'] }}</h3>
                    <p class="text-muted mb-0">{{ $active_upload_tab['description'] }}</p>
                </div>
                <button type="button" class="btn btn-outline-dark btn-sm" data-bs-toggle="modal" data-bs-target="#uploadPainelModal">Novo upload</button>
            </div>

            @if (! empty($active_upload_tab['tab_chart']))
                <script id="traffic-tab-chart-data" type="application/json">@json($active_upload_tab['tab_chart'])</script>
                <div class="panel mt-4">
                    <h3 class="mb-1">Evolução Mensal</h3>
                    <p class="text-muted mb-0 small">Últimos 12 meses com dados.</p>
                    <div id="trafficTabChart" class="mt-3" style="min-height:320px;"></div>
                </div>
            @endif

            <div class="row g-4 mt-1">
                @foreach ($active_upload_tab['metric_blocks'] as $block)
                    <div class="col-lg-6">
                        <div class="panel traffic-block-panel {{ ! empty($block['highlighted']) ? 'is-results' : '' }}">
                            <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                                <div>
                                    <h3 class="mb-1">{{ $block['title'] }}</h3>
                                    <p class="text-muted mb-0">{{ $block['description'] }}</p>
                                </div>
                                <div class="d-flex align-items-center gap-2">
                                    @if (! empty($block['filter_options']))
                                        <div class="crm-filter-dropdown" data-crm-filter-group="{{ $block['key'] }}" data-crm-filter-storage="{{ $active_upload_tab['key'] }}::{{ $block['key'] }}">
                                            <button type="button" class="btn btn-sm btn-outline-dark" data-crm-filter-toggle>
                                                Filtrar itens <span class="crm-filter-count" data-crm-filter-count>{{ count($block['filter_options']) }}</span>
                                            </button>
                                            <div class="crm-filter-dropdown-menu d-none" data-crm-filter-menu>
                                                <div class="crm-filter-dropdown-head">
                                                    <button type="button" class="btn btn-sm btn-link p-0" data-crm-filter-select-all>Marcar todos</button>
                                                    <button type="button" class="btn btn-sm btn-link p-0" data-crm-filter-clear>Limpar</button>
                                                </div>
                                                <div class="crm-filter-search-wrap">
                                                    <input type="text" class="form-control form-control-sm" placeholder="Buscar item..." data-crm-filter-search>
                                                </div>
                                                <div class="crm-filter-dropdown-list">
                                                    @foreach ($block['filter_options'] as $option)
                                                        <label class="form-check mb-2" data-crm-filter-item>
                                                            <input class="form-check-input" type="checkbox" checked data-crm-filter-option="{{ $option }}">
                                                            <span class="form-check-label">{{ $option }}</span>
                                                        </label>
                                                    @endforeach
                                                </div>
                                            </div>
                                        </div>
                                    @endif
                                    <button class="panel-collapse-btn" type="button" data-bs-toggle="collapse" data-bs-target="#panel-body-traffic-{{ $block['key'] }}" aria-expanded="true">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"></polyline></svg>
                                    </button>
                                </div>
                            </div>
                            <div class="collapse show" id="panel-body-traffic-{{ $block['key'] }}">
                                <div class="table-responsive mt-3">
                                    <table class="table align-middle traffic-summary-table mb-0">
                                        <thead><tr><th>Métrica</th><th>Valor</th><th>Variação</th></tr></thead>
                                        <tbody>
                                            @foreach ($block['rows'] as $row)
                                                <tr data-crm-row-label="{{ $row['label'] }}">
                                                    <td>
                                                        <span class="kpi-label">
                                                            {{ $row['label'] }}
                                                            @if (! empty($row['tooltip']))
                                                                <button type="button" class="kpi-help" data-bs-toggle="tooltip" title="{{ $row['tooltip'] }}">?</button>
                                                            @endif
                                                        </span>
                                                    </td>
                                                    <td><strong>{{ $row['current_value'] }}</strong></td>
                                                    <td class="{{ $row['variation_class'] }}" data-bs-toggle="tooltip" title="{{ $previous_month_label }}: {{ $row['previous_value'] }}">{{ $row['variation_value'] }}</td>
                                                </tr>
                                            @endforeach
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                @endforeach
            </div>

            <script id="traffic-blocks-data" type="application/json">@json($active_upload_tab['metric_blocks'])</script>

            <div class="panel mt-4">
                <h3>Tabela por campanha</h3>
                <div class="table-responsive">
                    <table class="table align-middle">
                        <thead><tr><th>Campanha</th><th>Investimento</th><th>Impressões</th><th>Alcance</th><th>Cliques</th><th>CTR</th><th>CPC</th><th>CPM</th><th>Resultados</th><th>CPL</th></tr></thead>
                        <tbody>
                        @forelse ($campaign_rows as $row)
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
                            <tr><td colspan="10">Nenhum dado para o filtro selecionado.</td></tr>
                        @endforelse
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="panel mt-4">
                <h3>Uploads Feitos</h3>
                <div class="table-responsive">
                    <table class="table align-middle">
                        <thead><tr><th>Arquivo</th><th>Referência</th><th>Período</th><th>Criado em</th><th>Ações</th></tr></thead>
                        <tbody>
                        @forelse ($uploads_list as $upload)
                            <tr>
                                <td>{{ $upload->arquivo }}</td>
                                <td>{{ $upload->nome_referencia }}</td>
                                <td>{{ $upload->data_inicio && $upload->data_fim ? br_date($upload->data_inicio).' - '.br_date($upload->data_fim) : '-' }}</td>
                                <td>{{ br_datetime($upload->created_at) }}</td>
                                <td>
                                    <form method="post" action="{{ route('campanhas.upload_delete', $upload->id) }}">
                                        @csrf
                                        @method('DELETE')
                                        <button class="btn btn-sm btn-outline-danger" type="submit">Excluir</button>
                                    </form>
                                </td>
                            </tr>
                        @empty
                            <tr><td colspan="5">Nenhum upload disponível.</td></tr>
                        @endforelse
                        </tbody>
                    </table>
                </div>
            </div>

        @elseif ($active_upload_tab && $active_upload_tab['panel_type'] === 'crm_vendas')
            <div class="dashboard-tab-header">
                <div>
                    <h3 class="mb-1">{{ $active_upload_tab['title'] }}</h3>
                    <p class="text-muted mb-0">{{ $active_upload_tab['description'] }}</p>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="text-muted small">{{ $active_upload_tab['config_name'] }}</span>
                    <button type="button" class="btn btn-outline-dark btn-sm" data-bs-toggle="modal" data-bs-target="#uploadPainelModal">Importar arquivo</button>
                </div>
            </div>

            @if (! empty($active_upload_tab['tab_chart']))
                <script id="crm-tab-chart-data" type="application/json">@json($active_upload_tab['tab_chart'])</script>
                <div class="panel mt-4">
                    <h3 class="mb-1">Evolução Mensal — Resultado</h3>
                    <p class="text-muted mb-0 small">Últimos 12 meses com dados.</p>
                    <div id="crmTabChart" class="mt-3" style="min-height:320px;"></div>
                </div>
            @endif

            <div class="row g-4 mt-1">
                @forelse ($active_upload_tab['category_blocks'] as $block)
                    <div class="{{ ($block['key'] ?? '') === 'vendedor' || ($block['chart_type'] ?? '') === 'pie' ? 'col-12' : 'col-lg-6' }}">
                        <div class="panel traffic-block-panel">
                            <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                                <div>
                                    <h3 class="mb-1">{{ $block['title'] }}</h3>
                                    <p class="text-muted mb-0">{{ $block['description'] }}</p>
                                </div>
                                <div class="d-flex align-items-center gap-2">
                                    @if (! empty($block['filter_options']))
                                        <div class="crm-filter-dropdown" data-crm-filter-group="{{ $block['key'] }}" data-crm-filter-storage="{{ $active_upload_tab['key'] }}::{{ $block['key'] }}">
                                            <button type="button" class="btn btn-sm btn-outline-dark" data-crm-filter-toggle>
                                                Filtrar itens <span class="crm-filter-count" data-crm-filter-count>{{ count($block['filter_options']) }}</span>
                                            </button>
                                            <div class="crm-filter-dropdown-menu d-none" data-crm-filter-menu>
                                                <div class="crm-filter-dropdown-head">
                                                    <button type="button" class="btn btn-sm btn-link p-0" data-crm-filter-select-all>Marcar todos</button>
                                                    <button type="button" class="btn btn-sm btn-link p-0" data-crm-filter-clear>Limpar</button>
                                                </div>
                                                <div class="crm-filter-search-wrap">
                                                    <input type="text" class="form-control form-control-sm" placeholder="Buscar item..." data-crm-filter-search>
                                                </div>
                                                <div class="crm-filter-dropdown-list">
                                                    @foreach ($block['filter_options'] as $option)
                                                        <label class="form-check mb-2" data-crm-filter-item>
                                                            <input class="form-check-input" type="checkbox" checked data-crm-filter-option="{{ $option }}">
                                                            <span class="form-check-label">{{ $option }}</span>
                                                        </label>
                                                    @endforeach
                                                </div>
                                            </div>
                                        </div>
                                    @endif
                                    <button class="panel-collapse-btn" type="button" data-bs-toggle="collapse" data-bs-target="#panel-body-crm-{{ $block['key'] }}" aria-expanded="true">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"></polyline></svg>
                                    </button>
                                </div>
                            </div>
                            <div class="collapse show" id="panel-body-crm-{{ $block['key'] }}">
                                @if (($block['chart_type'] ?? '') === 'pie' && ! empty($block['chart']))
                                    <div class="row mt-3 align-items-center g-0">
                                        <div class="col-md-5"><div id="crmCategoryChart-{{ $block['key'] }}" style="min-height:300px;"></div></div>
                                        <div class="col-md-7">
                                @endif
                                @if (! empty($block['rows']))
                                    <div class="table-responsive mt-3 {{ ($block['chart_type'] ?? '') === 'pie' ? 'ps-md-3' : '' }}">
                                        <table class="table align-middle traffic-summary-table mb-0">
                                            <thead><tr><th>Métrica</th><th>Valor</th><th>Variação</th></tr></thead>
                                            <tbody>
                                                @foreach ($block['rows'] as $row)
                                                    <tr data-crm-row-label="{{ $row['label'] }}">
                                                        <td @if(! empty($row['label_color'])) style="color: {{ $row['label_color'] }}; font-weight:700;" @endif>{{ $row['label'] }}</td>
                                                        <td><strong>{{ $row['current_value'] }}</strong></td>
                                                        <td class="{{ $row['variation_class'] }}" data-bs-toggle="tooltip" title="{{ $previous_month_label }}: {{ $row['previous_value'] }}">{{ $row['variation_value'] }}</td>
                                                    </tr>
                                                @endforeach
                                            </tbody>
                                        </table>
                                    </div>
                                @endif
                                @if (($block['chart_type'] ?? '') === 'pie' && ! empty($block['chart']))
                                        </div>
                                    </div>
                                @endif
                            </div>
                        </div>
                    </div>
                @empty
                    <div class="col-12"><div class="panel"><p class="text-muted mb-0">Ative métricas na configuração do painel para montar a aba de Vendas.</p></div></div>
                @endforelse
            </div>

            <script id="crm-category-blocks-data" type="application/json">@json($active_upload_tab['category_blocks'])</script>

            <div class="panel mt-4">
                <h3>Uploads do Painel</h3>
                <div class="table-responsive">
                    <table class="table align-middle">
                        <thead><tr><th>Arquivo</th><th>Criado em</th><th>Colunas</th><th>Ações</th></tr></thead>
                        <tbody>
                        @forelse ($panel_uploads_list as $upload)
                            <tr>
                                <td>{{ $upload->nome_arquivo }}</td>
                                <td>{{ br_datetime($upload->created_at) }}</td>
                                <td>{{ is_array($upload->colunas_detectadas_json) ? count($upload->colunas_detectadas_json) : 0 }}</td>
                                <td>
                                    <form method="post" action="{{ route('campanhas.panel_upload_delete', $upload->id) }}">
                                        @csrf
                                        @method('DELETE')
                                        <button class="btn btn-sm btn-outline-danger" type="submit">Excluir</button>
                                    </form>
                                </td>
                            </tr>
                        @empty
                            <tr><td colspan="4">Nenhum upload disponível.</td></tr>
                        @endforelse
                        </tbody>
                    </table>
                </div>
            </div>

        @elseif ($active_upload_tab && $active_upload_tab['panel_type'] === 'leads_eventos')
            @if (! empty($active_upload_tab['tab_chart']))
                <script id="leads-eventos-chart-data" type="application/json">@json($active_upload_tab['tab_chart'])</script>
            @endif
            <div class="dashboard-tab-header">
                <div>
                    <h3 class="mb-1">{{ $active_upload_tab['title'] }}</h3>
                    <p class="text-muted mb-0">{{ $active_upload_tab['description'] }}</p>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="text-muted small">{{ $active_upload_tab['config_name'] }}</span>
                    <button type="button" class="btn btn-outline-dark btn-sm" data-bs-toggle="modal" data-bs-target="#uploadPainelModal">Novo upload</button>
                </div>
            </div>
            <div class="panel mt-4">
                <h3 class="mb-1">Evolução Mensal — Pessoas Alcançadas</h3>
                <p class="text-muted mb-0 small">Últimos 12 meses com dados.</p>
                <div id="leadsEventosChart" class="mt-3" style="min-height:320px;"></div>
            </div>
            <div class="panel mt-4">
                <h3>Lista de Eventos</h3>
                <div class="table-responsive">
                    <table class="table align-middle">
                        <thead><tr><th>Evento</th><th>Data</th><th>Impacto</th><th>Pessoas alcançadas</th></tr></thead>
                        <tbody>
                        @forelse ($active_upload_tab['rows'] as $row)
                            <tr>
                                <td>{{ $row['evento'] }}</td>
                                <td>{{ br_date($row['data_evento']) }}</td>
                                <td>{{ $row['impacto'] }}</td>
                                <td>{{ br_number($row['leads_media'], 0) }}</td>
                            </tr>
                        @empty
                            <tr><td colspan="4">Sem dados disponíveis, adicione dados ao painel.</td></tr>
                        @endforelse
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="panel mt-4">
                <h3>Dados do Painel</h3>
                <div class="table-responsive">
                    <table class="table align-middle">
                        <thead><tr><th>Evento</th><th>Data</th><th>Impacto</th><th>Pessoas alcançadas</th><th>Criado em</th><th>Ações</th></tr></thead>
                        <tbody>
                        @forelse ($eventos_painel_list as $evento)
                            <tr>
                                <td>{{ $evento->nome_evento }}</td>
                                <td>{{ br_date($evento->data_evento) }}</td>
                                <td>{{ \Illuminate\Support\Str::headline($evento->impacto) }}</td>
                                <td>{{ br_number($evento->leads_media, 0) }}</td>
                                <td>{{ br_datetime($evento->created_at) }}</td>
                                <td>
                                    <form method="post" action="{{ route('campanhas.evento_painel_delete', $evento->id) }}">
                                        @csrf
                                        @method('DELETE')
                                        <button class="btn btn-sm btn-outline-danger" type="submit">Excluir</button>
                                    </form>
                                </td>
                            </tr>
                        @empty
                            <tr><td colspan="6">Nenhum dado cadastrado.</td></tr>
                        @endforelse
                        </tbody>
                    </table>
                </div>
            </div>

        @elseif ($active_upload_tab && $active_upload_tab['panel_type'] === 'redes_sociais')
            <div class="dashboard-tab-header">
                <div>
                    <h3 class="mb-1">{{ $active_upload_tab['title'] }}</h3>
                    <p class="text-muted mb-0">{{ $active_upload_tab['description'] }}</p>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="text-muted small">{{ $active_upload_tab['config_name'] }}</span>
                    <button type="button" class="btn btn-outline-dark btn-sm" data-bs-toggle="modal" data-bs-target="#uploadPainelModal">{{ $active_upload_tab['panel_type'] === 'leads_eventos' ? 'Importar arquivo' : 'Novo upload' }}</button>
                </div>
            </div>

            @if (! empty($active_upload_tab['tab_chart']))
                <script id="social-tab-chart-data" type="application/json">@json($active_upload_tab['tab_chart'])</script>
                <div class="panel mt-4">
                    <h3 class="mb-1">Evolução Mensal</h3>
                    <p class="text-muted mb-0 small">Últimos 12 meses com dados.</p>
                    <div id="socialTabChart" class="mt-3" style="min-height:320px;"></div>
                </div>
            @endif

            <div class="row g-4 mt-1">
                @foreach ($active_upload_tab['category_blocks'] as $block)
                    <div class="col-lg-6">
                        <div class="panel traffic-block-panel">
                            <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                                <div>
                                    <h3 class="mb-1">{{ $block['title'] }}</h3>
                                    <p class="text-muted mb-0">{{ $block['description'] }}</p>
                                </div>
                                <div class="d-flex align-items-center gap-2">
                                    @if (! empty($block['filter_options']))
                                        <div class="crm-filter-dropdown" data-crm-filter-group="{{ $block['key'] }}" data-crm-filter-storage="{{ $active_upload_tab['key'] }}::{{ $block['key'] }}">
                                            <button type="button" class="btn btn-sm btn-outline-dark" data-crm-filter-toggle>
                                                Filtrar itens <span class="crm-filter-count" data-crm-filter-count>{{ count($block['filter_options']) }}</span>
                                            </button>
                                            <div class="crm-filter-dropdown-menu d-none" data-crm-filter-menu>
                                                <div class="crm-filter-dropdown-head">
                                                    <button type="button" class="btn btn-sm btn-link p-0" data-crm-filter-select-all>Marcar todos</button>
                                                    <button type="button" class="btn btn-sm btn-link p-0" data-crm-filter-clear>Limpar</button>
                                                </div>
                                                <div class="crm-filter-search-wrap">
                                                    <input type="text" class="form-control form-control-sm" placeholder="Buscar item..." data-crm-filter-search>
                                                </div>
                                                <div class="crm-filter-dropdown-list">
                                                    @foreach ($block['filter_options'] as $option)
                                                        <label class="form-check mb-2" data-crm-filter-item>
                                                            <input class="form-check-input" type="checkbox" checked data-crm-filter-option="{{ $option }}">
                                                            <span class="form-check-label">{{ $option }}</span>
                                                        </label>
                                                    @endforeach
                                                </div>
                                            </div>
                                        </div>
                                    @endif
                                    <button class="panel-collapse-btn" type="button" data-bs-toggle="collapse" data-bs-target="#panel-body-social-{{ $block['key'] }}" aria-expanded="true">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"></polyline></svg>
                                    </button>
                                </div>
                            </div>
                            <div class="collapse show" id="panel-body-social-{{ $block['key'] }}">
                                <div class="table-responsive mt-3">
                                    <table class="table align-middle traffic-summary-table mb-0">
                                        <thead><tr><th>Métrica</th><th>Valor</th><th>Variação</th></tr></thead>
                                        <tbody>
                                            @foreach ($block['rows'] as $row)
                                                <tr data-crm-row-label="{{ $row['label'] }}">
                                                    <td>{{ $row['label'] }}</td>
                                                    <td><strong>{{ $row['current_value'] }}</strong></td>
                                                    <td class="{{ $row['variation_class'] }}" data-bs-toggle="tooltip" title="{{ $previous_month_label }}: {{ $row['previous_value'] }}">{{ $row['variation_value'] }}</td>
                                                </tr>
                                            @endforeach
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                @endforeach
            </div>

            <script id="social-category-blocks-data" type="application/json">@json($active_upload_tab['category_blocks'])</script>

            <div class="panel mt-4">
                <h3>Uploads do Painel</h3>
                <div class="table-responsive">
                    <table class="table align-middle">
                        <thead><tr><th>Arquivo</th><th>Tipo</th><th>Criado em</th><th>Colunas</th><th>Ações</th></tr></thead>
                        <tbody>
                        @forelse ($panel_uploads_list as $upload)
                            <tr>
                                <td>{{ $upload->nome_arquivo }}</td>
                                <td>{{ $upload->tipo_upload ?: '-' }}</td>
                                <td>{{ br_datetime($upload->created_at) }}</td>
                                <td>{{ is_array($upload->colunas_detectadas_json) ? count($upload->colunas_detectadas_json) : 0 }}</td>
                                <td>
                                    <form method="post" action="{{ route('campanhas.panel_upload_delete', $upload->id) }}">
                                        @csrf
                                        @method('DELETE')
                                        <button class="btn btn-sm btn-outline-danger" type="submit">Excluir</button>
                                    </form>
                                </td>
                            </tr>
                        @empty
                            <tr><td colspan="5">Nenhum upload disponível.</td></tr>
                        @endforelse
                        </tbody>
                    </table>
                </div>
            </div>

        @elseif ($dashboard_tab === 'analise_completa' && $analise_completa_tab)
            <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap mb-4">
                <div>
                    <h3 class="mb-1">Resumo Executivo</h3>
                    <p class="text-muted mb-0">{{ $analise_completa_tab['description'] }}</p>
                </div>
                @if ($empresa)
                    <form method="post" action="{{ route('relatorios.generate') }}" data-loading-title="Gerando Relatório" data-loading-text="Aguarde enquanto o relatório é montado.">
                        @csrf
                        <input type="hidden" name="data_inicio" value="{{ $current_start_iso }}">
                        <input type="hidden" name="data_fim" value="{{ $current_end_iso }}">
                        <input type="hidden" name="data_inicio_anterior" value="{{ $previous_start_iso }}">
                        <input type="hidden" name="data_fim_anterior" value="{{ $previous_end_iso }}">
                        <input type="hidden" name="titulo" value="Relatório {{ $empresa->nome }} {{ $mes_label }}">
                        <button type="submit" class="btn btn-dark">Gerar Relatório</button>
                    </form>
                @endif
            </div>

            @if (! empty($analise_completa_tab['tab_chart']))
                <script id="executive-tab-chart-data" type="application/json">@json($analise_completa_tab['tab_chart'])</script>
                <div class="panel mt-4">
                    <h3 class="mb-1">Evolução Mensal — Visão Geral</h3>
                    <p class="text-muted mb-0 small">Últimos 12 meses com dados.</p>
                    <div id="executiveTabChart" class="mt-3" style="min-height:320px;"></div>
                </div>
            @endif

            <div class="row g-3 mt-1">
                @foreach ($analise_completa_tab['top_cards'] as $item)
                    <div class="col-md-6 col-xl-3">
                        <div class="kpi-card h-100">
                            <span class="kpi-label">
                                {{ $item['label'] }}
                                @if (! empty($item['tooltip']))
                                    <button type="button" class="kpi-help" data-bs-toggle="tooltip" title="{{ $item['tooltip'] }}">?</button>
                                @endif
                            </span>
                            <strong>{{ $item['value'] }}</strong>
                        </div>
                    </div>
                @endforeach
            </div>

            <div class="row g-4 mt-1">
                @foreach ($analise_completa_tab['summary_panels'] as $panel)
                    <div class="col-lg-6">
                        <div class="panel traffic-block-panel h-100">
                            <h3 class="mb-1">{{ $panel['title'] }}</h3>
                            <p class="text-muted mb-0">{{ $panel['description'] }}</p>
                            <div class="table-responsive mt-3">
                                <table class="table align-middle traffic-summary-table mb-0">
                                    <thead><tr><th>Métrica</th><th>Valor</th><th>Variação</th></tr></thead>
                                    <tbody>
                                        @foreach ($panel['rows'] as $row)
                                            <tr>
                                                <td>{{ $row['label'] }}</td>
                                                <td><strong>{{ $row['current_value'] }}</strong></td>
                                                <td class="{{ $row['variation_class'] }}" data-bs-toggle="tooltip" title="{{ $previous_month_label }}: {{ $row['previous_value'] }}">{{ $row['variation_value'] }}</td>
                                            </tr>
                                        @endforeach
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                @endforeach
            </div>

            <div class="panel mt-4">
                <h3>Sinais dos Concorrentes</h3>
                <p class="text-muted mb-3">Resumo rápido de algumas ações e intensidade digital dos concorrentes monitorados.</p>
                <div class="table-responsive">
                    <table class="table align-middle mb-0">
                        <thead><tr><th>Concorrente</th><th>Atividade</th><th>Ads observados</th><th>Cadência</th></tr></thead>
                        <tbody>
                            @forelse ($analise_completa_tab['competitor_signals'] as $item)
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

            <div class="panel mt-4">
                <h3>Relatórios Gerados</h3>
                <div class="table-responsive">
                    <table class="table align-middle">
                        <thead><tr><th>Título</th><th>Período</th><th>Criado em</th><th></th></tr></thead>
                        <tbody>
                            @forelse ($relatorios_list as $relatorio)
                                <tr>
                                    <td>{{ $relatorio->titulo }}</td>
                                    <td>{{ br_date($relatorio->periodo_inicio) }} - {{ br_date($relatorio->periodo_fim) }}</td>
                                    <td>{{ br_datetime($relatorio->created_at) }}</td>
                                    <td class="d-flex gap-2">
                                        <a class="btn btn-sm btn-outline-dark" href="{{ route('relatorios.detail', $relatorio->id) }}">Abrir</a>
                                        <form method="post" action="{{ route('relatorios.delete', $relatorio->id) }}">
                                            @csrf
                                            @method('DELETE')
                                            <button class="btn btn-sm btn-outline-danger" type="submit">Excluir</button>
                                        </form>
                                    </td>
                                </tr>
                            @empty
                                <tr><td colspan="4">Nenhum relatório gerado ainda.</td></tr>
                            @endforelse
                        </tbody>
                    </table>
                </div>
            </div>

        @elseif ($dashboard_tab === 'concorrentes' && $concorrentes_tab)
            <div class="d-flex justify-content-between align-items-center mt-4 mb-3">
                <p class="text-muted mb-0">Base observável/importada de anúncios públicos dos concorrentes.</p>
                <div class="d-flex gap-2">
                    <a href="{{ route('concorrentes.instagram_import') }}" class="btn btn-dark">Novo Concorrente</a>
                    <a href="{{ route('concorrentes.import') }}" class="btn btn-outline-dark">Importar Concorrentes</a>
                </div>
            </div>
            <div class="panel">
                <div class="d-flex justify-content-between align-items-center gap-3 flex-wrap">
                    <div>
                        <h3 class="mb-1">Lista de Concorrentes</h3>
                        <p class="text-muted mb-0">Expanda ou recolha a lista para focar na análise digital.</p>
                    </div>
                    <button class="btn btn-outline-dark btn-sm" type="button" data-bs-toggle="collapse" data-bs-target="#concorrentesListaCollapse" aria-expanded="true">
                        Expandir / recolher lista
                    </button>
                </div>
                <div class="collapse show mt-4" id="concorrentesListaCollapse">
                    <div class="table-responsive">
                        <table class="table align-middle">
                            <thead><tr><th>Concorrente</th><th>Score</th><th>Última avaliação</th><th>Plataforma</th><th class="text-end">Ações</th></tr></thead>
                            <tbody>
                                @forelse ($concorrentes_tab['concorrentes_list'] as $ad)
                                    <tr>
                                        <td>
                                            <div class="d-flex align-items-center gap-2 flex-wrap">
                                                <span>{{ $ad['concorrente_nome'] }}</span>
                                                <span class="activity-pill {{ $ad['activity_class'] }}">{{ $ad['activity_label'] }}</span>
                                            </div>
                                        </td>
                                        <td><span class="activity-pill {{ $ad['score_digital_class'] }}">{{ $ad['score_digital_label'] }}</span></td>
                                        <td>{{ $ad['data_referencia'] ? br_date($ad['data_referencia']) : br_datetime($ad['created_at']) }}</td>
                                        <td>{{ $ad['plataforma'] }}</td>
                                        <td class="text-end">
                                            <a class="btn btn-sm btn-outline-secondary" href="{{ route('concorrentes.update', $ad['id']) }}">Editar</a>
                                            <form method="post" action="{{ route('concorrentes.delete', $ad['id']) }}" class="d-inline">
                                                @csrf
                                                @method('DELETE')
                                                <button class="btn btn-sm btn-outline-danger" type="submit">Excluir</button>
                                            </form>
                                        </td>
                                    </tr>
                                @empty
                                    <tr><td colspan="5">Nenhum anúncio concorrente cadastrado.</td></tr>
                                @endforelse
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        @endif
    </div>
</div>

@if ($upload_modal)
<div class="modal fade" id="uploadPainelModal" tabindex="-1" aria-labelledby="uploadPainelModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <form method="post" action="{{ route('campanhas.upload_store') }}" enctype="multipart/form-data">
                @csrf
                <input type="hidden" name="config_id" value="{{ $upload_modal['config_id'] }}">
                <input type="hidden" name="tab" value="{{ $upload_modal['tab'] }}">
                <input type="hidden" name="mes" value="{{ $upload_modal['month'] }}">
                <input type="hidden" name="ano" value="{{ $upload_modal['year'] }}">

                <div class="modal-header">
                    <h5 class="modal-title" id="uploadPainelModalLabel">
                        {{ $upload_modal['panel_type'] === 'leads_eventos' ? 'Importar arquivo' : 'Novo upload' }} - {{ $upload_modal['config_name'] }}
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                </div>
                <div class="modal-body">
                    @if (count($upload_modal['upload_type_options']) > 1)
                        <div class="mb-3">
                            <label for="uploadTipo" class="form-label fw-semibold">Tipo de arquivo</label>
                            <select name="tipo_upload" id="uploadTipo" class="form-select">
                                @foreach ($upload_modal['upload_type_options'] as $option)
                                    <option value="{{ $option['key'] }}">{{ $option['label'] }}</option>
                                @endforeach
                            </select>
                        </div>
                    @else
                        <input type="hidden" name="tipo_upload" value="{{ $upload_modal['upload_type_options'][0]['key'] ?? 'principal' }}">
                    @endif

                    <div>
                        <label for="uploadArquivo" class="form-label fw-semibold">Arquivo</label>
                        <input type="file" name="arquivo" id="uploadArquivo" class="form-control @error('arquivo') is-invalid @enderror" accept=".csv,.txt,.xls,.xlsx" required>
                        @error('arquivo')
                            <div class="invalid-feedback d-block">{{ $message }}</div>
                        @enderror
                    </div>

                    @if ($upload_modal['panel_type'] === 'trafego_pago')
                        <div class="form-text mt-2">O período será inferido automaticamente pelo arquivo, usando as colunas mapeadas no painel.</div>
                    @elseif ($upload_modal['panel_type'] === 'leads_eventos')
                        <div class="form-text mt-2">
                            Colunas esperadas: Nome do Evento, Data, Impacto e Leads Alcançados em Média.
                            <a href="{{ route('campanhas.evento_painel_template_download') }}">Baixar template</a>
                        </div>
                    @endif
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button type="submit" class="btn btn-dark">Enviar upload</button>
                </div>
            </form>
        </div>
    </div>
</div>
@endif
@endsection

@section('extra_js')
<script>
document.addEventListener('DOMContentLoaded', () => {
  const formatNumberBr = (value, decimals = 2) => {
    const number = Number(value ?? 0);
    if (Number.isNaN(number)) return value;
    return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: decimals }).format(number);
  };

  const renderChart = (nodeId, chart, chartType = 'line') => {
    const node = document.getElementById(nodeId);
    if (!node || !chart) return;
    const hasData = Array.isArray(chart.series) && chart.series.some((serie) => Array.isArray(serie.data) ? serie.data.some((value) => Number(value || 0) > 0) : false);
    if (!hasData && chartType !== 'pie') {
      node.innerHTML = '<div class="chart-empty-state">Sem dados disponíveis para o período.</div>';
      return;
    }
    if (chartType === 'pie') {
      new ApexCharts(node, {
        chart: { type: 'pie', height: 420, toolbar: { show: false } },
        colors: chart.colors || ['#175cd3', '#2d6a4f', '#f59e0b', '#dc2626', '#7c3aed', '#0f766e'],
        series: chart.series || [],
        labels: chart.labels || [],
        legend: { show: false }
      }).render();
      return;
    }
    new ApexCharts(node, {
      chart: { type: 'line', height: 360, toolbar: { show: false }, zoom: { enabled: false }, stacked: false },
      colors: chart.colors || ['#175cd3', '#2d6a4f', '#c67a1a', '#7c3aed', '#dc2626', '#0f766e'],
      series: chart.series || [],
      xaxis: { categories: chart.categories || [], labels: { style: { fontSize: '11px' } } },
      yaxis: { labels: { formatter(value) { return formatNumberBr(value, 2); } } },
      stroke: { curve: 'smooth', width: (chart.series || []).map((item) => item.type === 'line' ? 3 : 2) },
      fill: { type: (chart.series || []).some((item) => item.type === 'area') ? ['solid', 'gradient', 'gradient', 'gradient', 'gradient'] : 'solid' },
      dataLabels: { enabled: true, formatter(value) { return formatNumberBr(value, 0); }, style: { fontSize: '10px', fontWeight: '600' }, background: { enabled: true, borderRadius: 3, padding: 2, opacity: 0.85 }, offsetY: -6 },
      legend: { position: 'bottom' },
      tooltip: { shared: true, y: { formatter(value) { return formatNumberBr(value, 2); } } }
    }).render();
  };

  const bindFilterMenus = () => {
    const getSelected = (groupKey) => Array.from(document.querySelectorAll(`.crm-filter-dropdown[data-crm-filter-group="${groupKey}"] [data-crm-filter-option]`))
      .filter((input) => input.checked)
      .map((input) => input.getAttribute('data-crm-filter-option'));

    const updateCount = (groupKey) => {
      const root = document.querySelector(`.crm-filter-dropdown[data-crm-filter-group="${groupKey}"]`);
      const count = root?.querySelector('[data-crm-filter-count]');
      if (count) count.textContent = getSelected(groupKey).length;
    };

    const syncRows = (groupKey) => {
      const selected = getSelected(groupKey);
      document.querySelectorAll(`.crm-filter-dropdown[data-crm-filter-group="${groupKey}"]`).forEach((root) => {
        root.closest('.traffic-block-panel')?.querySelectorAll('[data-crm-row-label]').forEach((row) => {
          row.classList.toggle('d-none', !selected.includes(row.getAttribute('data-crm-row-label')));
        });
      });
      updateCount(groupKey);
      const storageKey = document.querySelector(`.crm-filter-dropdown[data-crm-filter-group="${groupKey}"]`)?.dataset.crmFilterStorage;
      if (storageKey) localStorage.setItem(`dashboard-filter:${storageKey}`, JSON.stringify(selected));
    };

    document.querySelectorAll('.crm-filter-dropdown').forEach((root) => {
      const groupKey = root.dataset.crmFilterGroup;
      const storageKey = root.dataset.crmFilterStorage;
      const saved = storageKey ? JSON.parse(localStorage.getItem(`dashboard-filter:${storageKey}`) || 'null') : null;
      if (Array.isArray(saved)) {
        root.querySelectorAll('[data-crm-filter-option]').forEach((input) => {
          input.checked = saved.includes(input.getAttribute('data-crm-filter-option'));
        });
      }
      root.querySelector('[data-crm-filter-toggle]')?.addEventListener('click', () => root.querySelector('[data-crm-filter-menu]')?.classList.toggle('d-none'));
      root.querySelector('[data-crm-filter-select-all]')?.addEventListener('click', () => {
        root.querySelectorAll('[data-crm-filter-option]').forEach((input) => input.checked = true);
        syncRows(groupKey);
      });
      root.querySelector('[data-crm-filter-clear]')?.addEventListener('click', () => {
        root.querySelectorAll('[data-crm-filter-option]').forEach((input) => input.checked = false);
        syncRows(groupKey);
      });
      root.querySelector('[data-crm-filter-search]')?.addEventListener('input', (event) => {
        const term = event.target.value.trim().toLowerCase();
        root.querySelectorAll('[data-crm-filter-item]').forEach((item) => item.classList.toggle('d-none', term && !item.textContent.toLowerCase().includes(term)));
      });
      root.querySelectorAll('[data-crm-filter-option]').forEach((input) => input.addEventListener('change', () => syncRows(groupKey)));
      syncRows(groupKey);
    });

    document.addEventListener('click', (event) => {
      if (!event.target.closest('.crm-filter-dropdown')) {
        document.querySelectorAll('[data-crm-filter-menu]').forEach((menu) => menu.classList.add('d-none'));
      }
    });
  };

  const trafficNode = document.getElementById('traffic-tab-chart-data');
  if (trafficNode) renderChart('trafficTabChart', JSON.parse(trafficNode.textContent));

  const crmNode = document.getElementById('crm-tab-chart-data');
  if (crmNode) renderChart('crmTabChart', JSON.parse(crmNode.textContent));

  const socialNode = document.getElementById('social-tab-chart-data');
  if (socialNode) renderChart('socialTabChart', JSON.parse(socialNode.textContent));

  const leadsNode = document.getElementById('leads-eventos-chart-data');
  if (leadsNode) renderChart('leadsEventosChart', JSON.parse(leadsNode.textContent));

  const executiveNode = document.getElementById('executive-tab-chart-data');
  if (executiveNode) renderChart('executiveTabChart', JSON.parse(executiveNode.textContent));

  const crmBlocks = document.getElementById('crm-category-blocks-data');
  if (crmBlocks) {
    JSON.parse(crmBlocks.textContent).forEach((block) => {
      if (block.chart && block.chart_type === 'pie') renderChart(`crmCategoryChart-${block.key}`, block.chart, 'pie');
    });
  }

  bindFilterMenus();
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach((el) => new bootstrap.Tooltip(el, { trigger: 'hover' }));
  document.addEventListener('shown.bs.collapse', () => window.dispatchEvent(new Event('resize')));
});
</script>
@endsection
