<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class CampanhaMetric extends Model
{
    protected $table = 'campanha_metrics';

    protected $fillable = [
        'upload_id', 'fingerprint', 'data', 'campanha',
        'investimento', 'impressoes', 'alcance', 'cliques',
        'ctr', 'cpc', 'cpm', 'resultados', 'cpl',
    ];

    protected $casts = [
        'data'        => 'date',
        'investimento' => 'decimal:2',
        'ctr'         => 'decimal:4',
        'cpc'         => 'decimal:4',
        'cpm'         => 'decimal:4',
        'resultados'  => 'decimal:2',
        'cpl'         => 'decimal:4',
    ];

    public function upload(): BelongsTo
    {
        return $this->belongsTo(UploadCampanha::class, 'upload_id');
    }
}
