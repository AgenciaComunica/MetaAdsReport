<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Relatorio extends Model
{
    protected $table = 'relatorios';

    protected $fillable = [
        'empresa_id', 'titulo', 'periodo_inicio', 'periodo_fim',
        'tipo_periodo', 'resumo_ia', 'insights_ia', 'html_renderizado',
    ];

    protected $casts = [
        'periodo_inicio' => 'date',
        'periodo_fim'    => 'date',
    ];

    public function empresa(): BelongsTo
    {
        return $this->belongsTo(Empresa::class, 'empresa_id');
    }
}
