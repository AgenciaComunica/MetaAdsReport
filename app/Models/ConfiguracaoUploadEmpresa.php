<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class ConfiguracaoUploadEmpresa extends Model
{
    protected $table = 'configuracoes_upload_empresa';

    protected $fillable = [
        'empresa_id', 'nome', 'tipo_documento', 'arquivo_exemplo',
        'nome_arquivo_exemplo', 'colunas_detectadas_json', 'preview_json',
        'mapeamento_json', 'campos_principais_json', 'metricas_painel_json',
        'configuracao_analise_json',
    ];

    protected $casts = [
        'colunas_detectadas_json'   => 'array',
        'preview_json'              => 'array',
        'mapeamento_json'           => 'array',
        'campos_principais_json'    => 'array',
        'metricas_painel_json'      => 'array',
        'configuracao_analise_json' => 'array',
    ];

    public function empresa(): BelongsTo
    {
        return $this->belongsTo(Empresa::class, 'empresa_id');
    }

    public function uploads_painel(): HasMany
    {
        return $this->hasMany(UploadPainel::class, 'configuracao_id');
    }

    public function eventos_painel(): HasMany
    {
        return $this->hasMany(EventoPainel::class, 'configuracao_id');
    }
}
