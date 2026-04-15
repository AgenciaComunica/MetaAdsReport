@php($empresa = $empresa ?? null)

<div class="row g-3">
    <div class="col-md-6">
        <label class="form-label">Nome</label>
        <input type="text" name="nome" class="form-control" value="{{ old('nome', $empresa->nome ?? '') }}" required>
    </div>
    <div class="col-md-3">
        <label class="form-label">CNPJ</label>
        <input type="text" name="cnpj" class="form-control" value="{{ old('cnpj', $empresa->cnpj ?? '') }}" placeholder="00.000.000/0000-00">
    </div>
    <div class="col-md-3">
        <label class="form-label">Segmento</label>
        <select name="segmento" class="form-select">
            <option value="">Selecione</option>
            @foreach ($segmentos as $value => $label)
                <option value="{{ $value }}" @selected(old('segmento', $empresa->segmento ?? '') === $value)>{{ $label }}</option>
            @endforeach
        </select>
    </div>

    <div class="col-md-6">
        <label class="form-label">Instagram da empresa</label>
        <input type="text" name="instagram_profile_url" class="form-control" value="{{ old('instagram_profile_url', $empresa->instagram_profile_url ?? '') }}" placeholder="@empresa ou https://instagram.com/empresa">
    </div>
    <div class="col-md-6">
        <label class="form-label">Busca para Ads Library</label>
        <input type="text" name="ads_biblioteca_query" class="form-control" value="{{ old('ads_biblioteca_query', $empresa->ads_biblioteca_query ?? '') }}" placeholder="Termo principal da marca para busca">
    </div>

    <div class="col-md-3">
        <label class="form-label">Seguidores</label>
        <input type="number" name="seguidores" min="0" class="form-control" value="{{ old('seguidores', $empresa->seguidores ?? 0) }}">
    </div>
    <div class="col-md-3">
        <label class="form-label">Posts públicos</label>
        <input type="number" name="posts_total_publicos" min="0" class="form-control" value="{{ old('posts_total_publicos', $empresa->posts_total_publicos ?? 0) }}">
    </div>
    <div class="col-md-3">
        <label class="form-label">Posts visíveis</label>
        <input type="number" name="feed_posts_visiveis" min="0" class="form-control" value="{{ old('feed_posts_visiveis', $empresa->feed_posts_visiveis ?? 0) }}">
    </div>
    <div class="col-md-3">
        <label class="form-label">Cadência do feed</label>
        <input type="text" name="feed_cadencia" class="form-control" value="{{ old('feed_cadencia', $empresa->feed_cadencia ?? '') }}" placeholder="Ex.: 3 posts por semana">
    </div>

    <div class="col-12">
        <label class="form-label">Redes sociais</label>
        <textarea name="redes_sociais_texto" class="form-control" rows="4" placeholder="Uma por linha. Use 'Rede | URL' quando quiser nomear.&#10;Instagram | https://instagram.com/suaempresa&#10;LinkedIn | https://linkedin.com/company/suaempresa">{{ old('redes_sociais_texto', $redes_sociais_texto ?? '') }}</textarea>
    </div>

    <div class="col-12">
        <label class="form-label">Observações</label>
        <textarea name="observacoes" class="form-control" rows="4" placeholder="Anotações gerais sobre a empresa.">{{ old('observacoes', $empresa->observacoes ?? '') }}</textarea>
    </div>

    <div class="col-12">
        <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" role="switch" name="ativo" value="1" @checked(old('ativo', $empresa->ativo ?? true))>
            <label class="form-check-label">Empresa ativa</label>
        </div>
    </div>
</div>
