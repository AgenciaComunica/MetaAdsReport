<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Empresa extends Model
{
    protected $table = 'empresas';

    protected $fillable = [
        'nome', 'cnpj', 'segmento', 'redes_sociais_json', 'instagram_profile_url',
        'ads_biblioteca_ativo', 'ads_biblioteca_query', 'ads_biblioteca_sinal',
        'ads_biblioteca_consultado_em', 'seguidores', 'posts_total_publicos',
        'feed_posts_visiveis', 'feed_posts_detalhes', 'feed_datas_publicadas',
        'feed_cadencia', 'feed_formatos', 'observacoes', 'ativo',
    ];

    protected $casts = [
        'redes_sociais_json'         => 'array',
        'feed_posts_detalhes'        => 'array',
        'feed_datas_publicadas'      => 'array',
        'feed_formatos'              => 'array',
        'ads_biblioteca_ativo'       => 'boolean',
        'ativo'                      => 'boolean',
        'ads_biblioteca_consultado_em' => 'datetime',
    ];

    public function configuracoes_upload(): HasMany
    {
        return $this->hasMany(ConfiguracaoUploadEmpresa::class, 'empresa_id');
    }

    public function uploads_campanha(): HasMany
    {
        return $this->hasMany(UploadCampanha::class, 'empresa_id');
    }

    public function anuncios_concorrentes(): HasMany
    {
        return $this->hasMany(ConcorrenteAd::class, 'empresa_id');
    }

    public function analises_concorrenciais(): HasMany
    {
        return $this->hasMany(AnaliseConcorrencial::class, 'empresa_id');
    }

    public function relatorios(): HasMany
    {
        return $this->hasMany(Relatorio::class, 'empresa_id');
    }

    public function getRedesSociaisAttribute(): array
    {
        return $this->redes_sociais_json ?? [];
    }
}
