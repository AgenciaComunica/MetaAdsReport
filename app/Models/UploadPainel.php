<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class UploadPainel extends Model
{
    protected $table = 'uploads_painel';

    protected $fillable = [
        'configuracao_id', 'arquivo', 'tipo_upload',
        'nome_arquivo', 'colunas_detectadas_json', 'preview_json',
    ];

    protected $casts = [
        'colunas_detectadas_json' => 'array',
        'preview_json'            => 'array',
    ];

    public function configuracao(): BelongsTo
    {
        return $this->belongsTo(ConfiguracaoUploadEmpresa::class, 'configuracao_id');
    }
}
