<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AnaliseConcorrencial extends Model
{
    protected $table = 'analises_concorrenciais';

    protected $fillable = [
        'empresa_id', 'concorrente_nome', 'titulo', 'conteudo', 'total_anuncios',
    ];

    public function empresa(): BelongsTo
    {
        return $this->belongsTo(Empresa::class, 'empresa_id');
    }
}
