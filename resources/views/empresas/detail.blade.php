@extends('layouts.app')

@section('page_title', 'Configurar Painéis')

@section('content')
<div class="panel mt-4">
    <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
        <div>
            <h3 class="mb-1">{{ $empresa->nome }}</h3>
            <p class="text-muted mb-0">{{ $empresa_observacoes }}</p>
        </div>
        <a href="{{ route('empresas.update', $empresa->id) }}" class="btn btn-outline-dark">Editar</a>
    </div>
</div>
<div class="panel mt-4">
    <h3>Configurações de Painel</h3>
    <div class="table-responsive">
        <table class="table align-middle">
            <thead><tr><th>Nome</th><th>Tipo</th><th>Ações</th></tr></thead>
            <tbody>
                @forelse ($configuracoes_upload as $config)
                    <tr>
                        <td>{{ $config->nome }}</td>
                        <td>{{ $config->tipo_documento }}</td>
                        <td>
                            <a href="{{ route('empresas.upload_config_update', [$empresa->id, $config->id]) }}" class="btn btn-sm btn-outline-dark">Configurar</a>
                        </td>
                    </tr>
                @empty
                    <tr><td colspan="3">Nenhuma configuração cadastrada.</td></tr>
                @endforelse
            </tbody>
        </table>
    </div>
</div>
@endsection
