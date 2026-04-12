<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class UploadCampanha extends Model
{
    protected $table = 'uploads_campanha';

    protected $fillable = [
        'empresa_id', 'arquivo', 'nome_referencia', 'data_inicio',
        'data_fim', 'periodo_tipo', 'colunas_mapeadas_json', 'observacoes_importacao',
    ];

    protected $casts = [
        'colunas_mapeadas_json' => 'array',
        'data_inicio'           => 'date',
        'data_fim'              => 'date',
    ];

    public function empresa(): BelongsTo
    {
        return $this->belongsTo(Empresa::class, 'empresa_id');
    }

    public function metricas(): HasMany
    {
        return $this->hasMany(CampanhaMetric::class, 'upload_id');
    }
}
