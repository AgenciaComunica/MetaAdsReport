<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class EventoPainel extends Model
{
    protected $table = 'eventos_painel';

    protected $fillable = [
        'configuracao_id', 'nome_evento', 'data_evento', 'impacto', 'leads_media',
    ];

    protected $casts = [
        'data_evento' => 'date',
    ];

    public function configuracao(): BelongsTo
    {
        return $this->belongsTo(ConfiguracaoUploadEmpresa::class, 'configuracao_id');
    }
}
