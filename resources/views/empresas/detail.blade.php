@extends('layouts.app')

@section('page_title', 'Configurar Painéis')

@section('content')
<div class="panel mt-4">
    <div class="d-flex justify-content-between align-items-start gap-3 flex-wrap">
        <div>
            <h3 class="mb-1">{{ $empresa->nome }}</h3>
            <p class="text-muted mb-0">{{ $empresa_observacoes }}</p>
        </div>
        <div class="d-flex gap-2 flex-wrap">
            <a href="{{ route('empresas.panels', $empresa->id) }}" class="btn btn-outline-secondary">Configurar Painéis</a>
            <a href="{{ route('empresas.update', $empresa->id) }}" class="btn btn-outline-dark">Editar</a>
        </div>
    </div>
</div>
<div class="panel mt-4">
    <h3 class="mb-3">Informações da Empresa</h3>
    <div class="row g-3">
        <div class="col-md-4">
            <div><strong>CNPJ</strong></div>
            <div class="text-muted">{{ $empresa->cnpj ?: 'Não informado' }}</div>
        </div>
        <div class="col-md-4">
            <div><strong>Segmento</strong></div>
            <div class="text-muted">{{ $empresa->segmento ?: 'Não informado' }}</div>
        </div>
        <div class="col-md-4">
            <div><strong>Status</strong></div>
            <div class="text-muted">{{ $empresa->ativo ? 'Ativa' : 'Inativa' }}</div>
        </div>
        <div class="col-md-6">
            <div><strong>Instagram</strong></div>
            <div class="text-muted">{{ $empresa->instagram_profile_url ?: 'Não informado' }}</div>
        </div>
        <div class="col-md-6">
            <div><strong>Busca Ads Library</strong></div>
            <div class="text-muted">{{ $empresa->ads_biblioteca_query ?: 'Não informado' }}</div>
        </div>
        <div class="col-md-3">
            <div><strong>Seguidores</strong></div>
            <div class="text-muted">{{ number_format((float) $empresa->seguidores, 0, ',', '.') }}</div>
        </div>
        <div class="col-md-3">
            <div><strong>Posts públicos</strong></div>
            <div class="text-muted">{{ number_format((float) $empresa->posts_total_publicos, 0, ',', '.') }}</div>
        </div>
        <div class="col-md-3">
            <div><strong>Posts visíveis</strong></div>
            <div class="text-muted">{{ number_format((float) $empresa->feed_posts_visiveis, 0, ',', '.') }}</div>
        </div>
        <div class="col-md-3">
            <div><strong>Cadência</strong></div>
            <div class="text-muted">{{ $empresa->feed_cadencia ?: 'Não informada' }}</div>
        </div>
        <div class="col-12">
            <div><strong>Redes sociais</strong></div>
            @if (!empty($empresa->redes_sociais))
                <div class="mt-2 d-flex flex-wrap gap-2">
                    @foreach ($empresa->redes_sociais as $social)
                        @php
                            $label = is_array($social)
                                ? trim(((string) ($social['rede'] ?? '')) . ($social['url'] ?? '' ? ' | ' . $social['url'] : ''))
                                : (string) $social;
                        @endphp
                        @if ($label !== '')
                            <span class="badge text-bg-light border">{{ $label }}</span>
                        @endif
                    @endforeach
                </div>
            @else
                <div class="text-muted">Nenhuma rede social cadastrada.</div>
            @endif
        </div>
    </div>
</div>
@endsection
