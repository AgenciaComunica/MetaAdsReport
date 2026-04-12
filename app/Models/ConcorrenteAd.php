<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ConcorrenteAd extends Model
{
    protected $table = 'concorrente_ads';

    protected $fillable = [
        'empresa_id', 'concorrente_nome', 'texto_principal', 'titulo', 'descricao',
        'cta', 'plataforma', 'link', 'data_referencia', 'categoria',
        'ads_biblioteca_ativo', 'ads_biblioteca_query', 'ads_biblioteca_sinal',
        'ads_biblioteca_consultado_em', 'seguidores', 'posts_total_publicos',
        'feed_posts_visiveis', 'feed_posts_detalhes', 'feed_datas_publicadas',
        'feed_cadencia', 'feed_formatos', 'observacoes',
    ];

    protected $casts = [
        'ads_biblioteca_ativo'        => 'boolean',
        'ads_biblioteca_consultado_em' => 'datetime',
        'data_referencia'             => 'date',
        'feed_posts_detalhes'         => 'array',
        'feed_datas_publicadas'       => 'array',
        'feed_formatos'               => 'array',
    ];

    public function empresa(): BelongsTo
    {
        return $this->belongsTo(Empresa::class, 'empresa_id');
    }
}
