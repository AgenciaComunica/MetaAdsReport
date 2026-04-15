@extends('layouts.app')

@section('page_title', 'Configurar Painéis')

@section('page_actions')
    <a href="{{ route('empresas.detail', $empresa->id) }}" class="btn btn-outline-secondary">Voltar para Empresa</a>
@endsection

@section('content')
<div class="panel mt-4">
    <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
        <div>
            <h2 class="mb-1">{{ $empresa->nome }}</h2>
            <p class="text-muted mb-0">{{ $empresa_observacoes ?: 'Defina os painéis da empresa, como os arquivos são enviados e mapeados e quais análises alimentarão o dashboard.' }}</p>
        </div>
        <a href="{{ route('empresas.update', $empresa->id) }}" class="btn btn-outline-dark">Editar Empresa</a>
    </div>
</div>

<section class="mt-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
            <h3 class="mb-1">Configurar Painéis</h3>
            <p class="text-muted mb-0">Defina os painéis da empresa, como os arquivos são enviados e mapeados e quais análises alimentarão o dashboard.</p>
        </div>
    </div>

    <div class="upload-config-grid">
        <button
            type="button"
            class="upload-config-placeholder"
            data-bs-toggle="modal"
            data-bs-target="#novoPainelModal"
            aria-label="Adicionar painel"
        >
            <span class="upload-config-plus">+</span>
            <span class="upload-config-label">Adicionar Painel</span>
            <span class="text-muted">Clique para criar uma nova configuração de painel.</span>
        </button>

        @foreach ($configuracoes_upload as $config)
            <article class="panel upload-config-card">
                <span class="eyebrow">Configuração ativa</span>
                <h4 class="mb-2">{{ $config->nome }}</h4>
                <p class="text-muted mb-2">
                    Tipo:
                    @if ($config->tipo_documento)
                        {{ $type_options[$config->tipo_documento] ?? $config->tipo_documento }}
                    @else
                        Não definido
                    @endif
                </p>
                @if ($config->nome_arquivo_exemplo)
                    <p class="text-muted small mb-3">Arquivo base: {{ $config->nome_arquivo_exemplo }}</p>
                @else
                    <p class="text-muted small mb-3">Nenhum arquivo de exemplo configurado.</p>
                @endif
                <div class="d-flex gap-2 mt-auto">
                    <a href="{{ route('empresas.upload_config_update', [$empresa->id, $config->id]) }}" class="btn btn-dark flex-grow-1">Configurar Painel</a>
                    <button type="button" class="btn btn-outline-danger" data-bs-toggle="modal" data-bs-target="#excluirPainelModal{{ $config->id }}">Excluir</button>
                </div>
            </article>
        @endforeach
    </div>
</section>

<div class="modal fade" id="novoPainelModal" tabindex="-1" aria-labelledby="novoPainelModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <form method="post" action="{{ route('empresas.upload_config_create', $empresa->id) }}">
                @csrf
                <div class="modal-header">
                    <h5 class="modal-title" id="novoPainelModalLabel">Nova configuração de painel</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-0">
                        <label class="form-label">Nome do painel</label>
                        <input type="text" name="nome" class="form-control" placeholder="Ex.: Ads Digital, Vendas, Presença Digital" required>
                        <p class="text-muted small mt-2 mb-0">O tipo do painel e o mapeamento serão definidos na próxima tela.</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancelar</button>
                    <button type="submit" class="btn btn-dark">Criar painel</button>
                </div>
            </form>
        </div>
    </div>
</div>

@foreach ($configuracoes_upload as $config)
    <div class="modal fade" id="excluirPainelModal{{ $config->id }}" tabindex="-1" aria-labelledby="excluirPainelModalLabel{{ $config->id }}" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <form method="post" action="{{ route('empresas.upload_config_delete', [$empresa->id, $config->id]) }}">
                    @csrf
                    @method('DELETE')
                    <div class="modal-header">
                        <h5 class="modal-title" id="excluirPainelModalLabel{{ $config->id }}">Excluir configuração</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                    </div>
                    <div class="modal-body">
                        <p class="mb-2">Tem certeza que deseja excluir <strong>{{ $config->nome }}</strong>?</p>
                        <p class="text-muted mb-0">O arquivo de exemplo e o mapeamento salvo desta configuração serão removidos.</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancelar</button>
                        <button type="submit" class="btn btn-danger">Confirmar exclusão</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
@endforeach
@endsection
