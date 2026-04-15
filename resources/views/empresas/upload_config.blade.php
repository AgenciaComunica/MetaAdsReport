@extends('layouts.app')

@section('page_title', 'Configurar Painel')

@section('page_actions')
    <div class="d-flex gap-2 flex-wrap">
        <a href="{{ route('empresas.panels', $empresa->id) }}" class="btn btn-outline-dark">Voltar para Configurações</a>
        <button class="btn btn-dark" type="submit" form="configurarPainelForm" name="action" value="salvar">Salvar configuração</button>
    </div>
@endsection

@section('content')
<div class="panel mt-4">
    <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
        <div>
            <span class="text-uppercase small text-muted">Empresa</span>
            <h2 class="mb-1">{{ $empresa->nome }}</h2>
            <p class="text-muted mb-0">
                @if ($document_type)
                    Painel configurável do tipo {{ $type_options[$document_type] ?? $document_type }}.
                @else
                    Defina o tipo do painel, envie o arquivo e clique em Mapear para abrir o mapeamento.
                @endif
            </p>
        </div>
    </div>
</div>

<form id="configurarPainelForm" method="post" action="{{ route('empresas.upload_config_update.put', [$empresa->id, $config->id]) }}" enctype="multipart/form-data" class="panel mt-4 form-panel">
    @csrf
    @method('PUT')

    <div class="row g-4">
        <div class="col-lg-4">
            <h3 class="mb-3">Documento</h3>
            <div class="mb-3">
                <label class="form-label">Nome</label>
                <input type="text" name="nome" class="form-control" value="{{ old('nome', $config->nome) }}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Tipo do documento</label>
                <select name="tipo_documento" class="form-select" required>
                    <option value="">Selecione</option>
                    @foreach ($type_options as $value => $label)
                        <option value="{{ $value }}" @selected(old('tipo_documento', $document_type) === $value)>{{ $label }}</option>
                    @endforeach
                </select>
            </div>

            @if ($document_type === 'redes_sociais')
                <div class="mb-3">
                    <label class="form-label">Tipo Digital</label>
                    <select name="digital_type" class="form-select">
                        @foreach ($digital_type_options as $value => $label)
                            <option value="{{ $value }}" @selected(old('digital_type', $digital_type) === $value)>{{ $label }}</option>
                        @endforeach
                    </select>
                </div>
            @elseif ($document_type === 'trafego_pago')
                <div class="mb-3">
                    <label class="form-label">Tipo de Ads</label>
                    <select name="ads_type" class="form-select">
                        @foreach ($ads_type_options as $value => $label)
                            <option value="{{ $value }}" @selected(old('ads_type', $ads_type) === $value)>{{ $label }}</option>
                        @endforeach
                    </select>
                </div>
            @endif

            @if ($document_type !== 'leads_eventos')
                <div class="mb-3">
                    <label class="form-label">Arquivo exemplo</label>
                    <input type="file" name="arquivo_exemplo" class="form-control" accept=".csv,.txt,.xlsx,.xls">
                </div>

                @if ($document_type === 'redes_sociais')
                    <div class="mb-3">
                        <label class="form-label">Tipo do arquivo de exemplo</label>
                        <select name="social_example_kind" class="form-select">
                            @foreach ($social_mapping_types as $type)
                                <option value="{{ $type['key'] }}" @selected(old('social_example_kind', $social_example_kind) === $type['key'])>{{ $type['label'] }}</option>
                            @endforeach
                        </select>
                    </div>
                @endif

                <div class="d-flex flex-wrap gap-2 align-items-center">
                    <button class="btn btn-outline-dark" type="submit" name="action" value="mapear">Mapear</button>
                    @if ($has_example_file)
                        <button class="btn btn-outline-secondary" type="submit" name="action" value="limpar_arquivo">Limpar planilha exemplo</button>
                    @endif
                </div>

                @if ($config->nome_arquivo_exemplo)
                    <p class="text-muted small mb-0 mt-2">Arquivo de exemplo: {{ $config->nome_arquivo_exemplo }}</p>
                @else
                    <p class="text-muted small mb-0 mt-2">Selecione o tipo, envie o arquivo e clique em Mapear.</p>
                @endif
            @else
                <p class="text-muted small mb-0">Esse painel usa entrada manual no dashboard. Basta salvar a configuração para começar a cadastrar eventos.</p>
            @endif
        </div>
    </div>

    <div class="panel mt-4">
        <h3 class="mb-3">Análise do Painel</h3>

        @if ($document_type === 'redes_sociais')
            <div class="row g-3 mb-4">
                <div class="col-lg-6">
                    <div class="panel">
                        <h4 class="mb-2">Composição de Receita</h4>
                        <p class="text-muted small mb-3">Define quanto da base operacional migra de Operação para Marketing com base no alcance social do período.</p>
                        <label class="form-label">Percentual de receita a cada 1k de alcance da conta</label>
                        <input type="number" step="0.01" min="0" name="social_receita_percentual_por_1k_alcance" class="form-control" value="{{ old('social_receita_percentual_por_1k_alcance', $social_receita_percentual_por_1k_alcance) }}">
                    </div>
                </div>
            </div>
        @elseif ($document_type === 'leads_eventos')
            <div class="row g-3 mb-4">
                <div class="col-lg-6">
                    <div class="panel">
                        <h4 class="mb-2">Composição de Receita</h4>
                        <p class="text-muted small mb-3">Define quanto da base operacional migra de Operação para Marketing com base no alcance presencial dos eventos.</p>
                        <label class="form-label">Percentual de receita a cada 1k pessoas alcançadas</label>
                        <input type="number" step="0.01" min="0" name="eventos_receita_percentual_por_1k_alcance" class="form-control" value="{{ old('eventos_receita_percentual_por_1k_alcance', $eventos_receita_percentual_por_1k_alcance) }}">
                    </div>
                </div>
            </div>
        @endif

        @if ($document_type === 'crm_vendas')
            <div class="row g-3 mb-4">
                <div class="col-lg-6">
                    <div class="panel">
                        <h4 class="mb-2">Classificação de Origem Paga</h4>
                        <label class="form-label">Parâmetro de tráfego pago: contém</label>
                        <input type="text" name="crm_origem_paga_contem" class="form-control" placeholder="Ex.: utm_source=meta, gclid, fbclid" value="{{ old('crm_origem_paga_contem', $crm_origem_paga_contem) }}">
                    </div>
                </div>
            </div>
        @endif

        @if (! empty($metric_groups))
            <p class="text-muted small">Selecione quais métricas aparecem na tabela, no gráfico e quais categorias terão filtro no dashboard.</p>
            <div class="row g-3">
                @foreach ($metric_groups as $group)
                    <div class="col-lg-6">
                        <div class="panel h-100">
                            <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
                                <div>
                                    <h4 class="mb-1">{{ $group['label'] }}</h4>
                                    <p class="text-muted mb-0">{{ $group['description'] }}</p>
                                </div>
                                <div class="form-check form-switch mb-0">
                                    <input class="form-check-input" type="checkbox" role="switch" name="filter_enabled__{{ $group['key'] }}" value="1" @checked(old('filter_enabled__'.$group['key'], $group['filter_enabled']))>
                                    <label class="form-check-label">Habilitar filtro</label>
                                </div>
                            </div>
                            <div class="table-responsive mt-3">
                                <table class="table align-middle mb-0">
                                    <thead>
                                        <tr>
                                            <th>Métrica</th>
                                            <th class="text-center">Tabela</th>
                                            <th class="text-center">Gráfico</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        @foreach ($group['metrics'] as $metric)
                                            <tr>
                                                <td>{{ $metric['label'] }}</td>
                                                <td class="text-center">
                                                    <div class="form-check d-inline-flex justify-content-center mb-0">
                                                        <input class="form-check-input" type="checkbox" name="metric_table__{{ $metric['key'] }}" value="1" @checked(old('metric_table__'.$metric['key'], $metric['table_enabled']))>
                                                    </div>
                                                </td>
                                                <td class="text-center">
                                                    @if ($metric['chart_allowed'])
                                                        <div class="form-check d-inline-flex justify-content-center mb-0">
                                                            <input class="form-check-input" type="checkbox" name="metric_chart__{{ $metric['key'] }}" value="1" @checked(old('metric_chart__'.$metric['key'], $metric['chart_enabled']))>
                                                        </div>
                                                    @else
                                                        <span class="text-muted small">-</span>
                                                    @endif
                                                </td>
                                            </tr>
                                        @endforeach
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                @endforeach
            </div>
        @else
            <p class="text-muted mb-0">Defina o tipo do painel para configurar as métricas exibidas.</p>
        @endif
    </div>

    @if ($document_type !== 'leads_eventos')
        <div class="panel mt-4">
            <h3 class="mb-3">Mapeamento do Sistema</h3>
            @if ($document_type === 'redes_sociais')
                @if (! empty($mapping_sections))
                    <div class="row g-4">
                        @foreach ($mapping_sections as $section)
                            <div class="col-lg-6">
                                <div class="panel h-100">
                                    <h4 class="mb-1">{{ $section['label'] }}</h4>
                                    <p class="text-muted mb-3">{{ $section['file_name'] ?: 'Faça o mapeamento específico para esta fonte.' }}</p>
                                    <div class="table-responsive">
                                        <table class="table align-middle">
                                            <thead>
                                                <tr>
                                                    <th>Campo do sistema</th>
                                                    <th>Campo do arquivo</th>
                                                    <th class="text-center">Principal</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                @foreach ($section['rows'] as $row)
                                                    <tr>
                                                        <td>
                                                            <strong>{{ $row['label'] }}</strong>
                                                            @if ($row['required'])
                                                                <span class="badge text-bg-dark ms-2">Obrigatório</span>
                                                            @endif
                                                        </td>
                                                        <td>
                                                            <select name="map__{{ $section['key'] }}__{{ $row['key'] }}" class="form-select">
                                                                <option value="">Selecione</option>
                                                                @foreach ($row['options'] as $option)
                                                                    <option value="{{ $option }}" @selected(old('map__'.$section['key'].'__'.$row['key'], $row['selected']) === $option)>{{ $option }}</option>
                                                                @endforeach
                                                            </select>
                                                        </td>
                                                        <td class="text-center">
                                                            <div class="form-check d-inline-flex justify-content-center">
                                                                <input class="form-check-input" type="checkbox" name="primary__{{ $section['key'] }}__{{ $row['key'] }}" value="1" @checked(old('primary__'.$section['key'].'__'.$row['key'], $row['primary']))>
                                                            </div>
                                                        </td>
                                                    </tr>
                                                @endforeach
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                        @endforeach
                    </div>
                @else
                    <p class="text-muted mb-0">O mapeamento do sistema aparece depois que você envia o arquivo e clica em <strong>Mapear</strong>.</p>
                @endif
            @elseif (! empty($mapping_rows))
                <div class="table-responsive">
                    <table class="table align-middle">
                        <thead>
                            <tr>
                                <th>Campo do sistema</th>
                                <th>Campo do arquivo</th>
                                <th class="text-center">Principal</th>
                            </tr>
                        </thead>
                        <tbody>
                            @foreach ($mapping_rows as $row)
                                <tr>
                                    <td>
                                        <strong>{{ $row['label'] }}</strong>
                                        @if ($row['required'])
                                            <span class="badge text-bg-dark ms-2">Obrigatório</span>
                                        @endif
                                    </td>
                                    <td>
                                        <select name="map__{{ $row['key'] }}" class="form-select">
                                            <option value="">Selecione</option>
                                            @foreach ($row['options'] as $option)
                                                <option value="{{ $option }}" @selected(old('map__'.$row['key'], $row['selected']) === $option)>{{ $option }}</option>
                                            @endforeach
                                        </select>
                                    </td>
                                    <td class="text-center">
                                        <div class="form-check d-inline-flex justify-content-center">
                                            <input class="form-check-input" type="checkbox" name="primary__{{ $row['key'] }}" value="1" @checked(old('primary__'.$row['key'], $row['primary']))>
                                        </div>
                                    </td>
                                </tr>
                            @endforeach
                        </tbody>
                    </table>
                </div>
            @else
                <p class="text-muted mb-0">O mapeamento do sistema aparece depois que você envia o arquivo e clica em <strong>Mapear</strong>.</p>
            @endif
        </div>

        <div class="panel mt-4">
            <h3 class="mb-3">Leitura prévia do arquivo</h3>
            @if ($document_type === 'redes_sociais' && ! empty($mapping_sections))
                <ul class="nav nav-tabs dashboard-data-tabs mb-3" role="tablist">
                    @foreach ($mapping_sections as $section)
                        <li class="nav-item" role="presentation">
                            <button class="nav-link {{ $loop->first ? 'active' : '' }}" data-bs-toggle="tab" data-bs-target="#social-preview-{{ $section['key'] }}" type="button">
                                {{ $section['label'] }}
                            </button>
                        </li>
                    @endforeach
                </ul>
                <div class="tab-content">
                    @foreach ($mapping_sections as $section)
                        <div class="tab-pane fade {{ $loop->first ? 'show active' : '' }}" id="social-preview-{{ $section['key'] }}">
                            @if (! empty($section['preview_columns']))
                                <p class="text-muted mb-2">Colunas detectadas: {{ implode(', ', $section['preview_columns']) }}</p>
                                <div class="table-responsive">
                                    <table class="table align-middle">
                                        <thead>
                                            <tr>
                                                @foreach ($section['preview_columns'] as $column)
                                                    <th>{{ $column }}</th>
                                                @endforeach
                                            </tr>
                                        </thead>
                                        <tbody>
                                            @foreach ($section['preview_rows'] as $row)
                                                <tr>
                                                    @foreach ($section['preview_columns'] as $column)
                                                        <td>{{ $row[$column] ?? '' }}</td>
                                                    @endforeach
                                                </tr>
                                            @endforeach
                                        </tbody>
                                    </table>
                                </div>
                            @else
                                <p class="text-muted mb-0">O preview de {{ strtolower($section['label']) }} aparece depois da ação Mapear.</p>
                            @endif
                        </div>
                    @endforeach
                </div>
            @elseif (! empty($preview_columns))
                <p class="text-muted mb-2">Colunas detectadas: {{ implode(', ', $preview_columns) }}</p>
                <div class="table-responsive">
                    <table class="table align-middle">
                        <thead>
                            <tr>
                                @foreach ($preview_columns as $column)
                                    <th>{{ $column }}</th>
                                @endforeach
                            </tr>
                        </thead>
                        <tbody>
                            @foreach ($preview_rows as $row)
                                <tr>
                                    @foreach ($preview_columns as $column)
                                        <td>{{ $row[$column] ?? '' }}</td>
                                    @endforeach
                                </tr>
                            @endforeach
                        </tbody>
                    </table>
                </div>
            @else
                <p class="text-muted mb-0">O preview do arquivo aparece depois da ação Mapear.</p>
            @endif
        </div>
    @endif
</form>
@endsection
