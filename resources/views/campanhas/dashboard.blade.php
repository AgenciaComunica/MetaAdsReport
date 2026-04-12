@extends('layouts.app')

@section('page_title', 'Dashboard')

@section('page_actions')
    @if ($empresa)
        <a href="{{ route('empresas.detail', $empresa->id) }}" class="btn btn-outline-dark">Configurar Painéis</a>
    @endif
@endsection

@section('content')
<div class="panel mt-4 form-panel">
    <div class="d-flex align-items-center gap-3 flex-wrap">
        <form method="get" id="monthSelectorForm" class="d-flex align-items-center gap-2">
            <input type="hidden" name="tab" value="{{ $dashboard_tab }}">
            <label for="monthSelect" class="form-label mb-0 fw-semibold text-nowrap">Período</label>
            <select id="monthSelect" name="mes" class="form-select form-select-sm" style="width:auto;" onchange="this.form.submit()">
                @foreach ($meses_disponiveis as $mes)
                    <option value="{{ $mes['value'] }}" @if ($mes['value'] === $mes_param) selected @endif>{{ $mes['label'] }}</option>
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
                <a href="{{ route('campanhas.dashboard', ['tab' => $tab['key']]) }}" class="nav-link @if ($dashboard_tab === $tab['key']) active @endif">
                    {{ $tab['title'] }}
                </a>
            </li>
        @endforeach
    </ul>
    <div class="pt-4">
        <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
            <div>
                <h3 class="mb-1">Ads Digital</h3>
                <p class="text-muted mb-0">Painel base de campanhas, comparando mês atual e anterior.</p>
            </div>
        </div>

        <div class="panel mt-4">
            <h3>Tabela por campanha</h3>
            <div class="table-responsive">
                <table class="table align-middle">
                    <thead>
                        <tr>
                            <th>Campanha</th>
                            <th>Investimento</th>
                            <th>Impressões</th>
                            <th>Alcance</th>
                            <th>Cliques</th>
                            <th>CTR</th>
                            <th>CPC</th>
                            <th>CPM</th>
                            <th>Resultados</th>
                            <th>CPL</th>
                        </tr>
                    </thead>
                    <tbody>
                        @forelse ($campaign_rows as $row)
                            <tr>
                                <td>{{ $row['campanha'] }}</td>
                                <td>R$ {{ number_format($row['investimento'], 2, ',', '.') }}</td>
                                <td>{{ $row['impressoes'] }}</td>
                                <td>{{ $row['alcance'] }}</td>
                                <td>{{ $row['cliques'] }}</td>
                                <td>{{ number_format($row['ctr'], 2, ',', '.') }}%</td>
                                <td>R$ {{ number_format($row['cpc'], 2, ',', '.') }}</td>
                                <td>R$ {{ number_format($row['cpm'], 2, ',', '.') }}</td>
                                <td>{{ number_format($row['resultados'], 2, ',', '.') }}</td>
                                <td>R$ {{ number_format($row['cpl'], 2, ',', '.') }}</td>
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
                                <td>
                                    @if ($upload->data_inicio && $upload->data_fim)
                                        {{ $upload->data_inicio->format('d/m/Y') }} - {{ $upload->data_fim->format('d/m/Y') }}
                                    @else
                                        -
                                    @endif
                                </td>
                                <td>{{ $upload->created_at?->format('d/m/Y H:i') }}</td>
                                <td><a class="btn btn-sm btn-outline-danger" href="{{ route('campanhas.upload_delete', $upload->id) }}">Excluir</a></td>
                            </tr>
                        @empty
                            <tr><td colspan="5">Nenhum upload disponível.</td></tr>
                        @endforelse
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
@endsection
