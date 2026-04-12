<?php

namespace App\Services;

use App\Models\ConcorrenteAd;
use Carbon\Carbon;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Http;

class ConcorrenteService
{
    public const ACTIVITY_META = [
        'alto' => ['label' => 'Alto Ads', 'class_name' => 'is-high', 'color' => '#b42318'],
        'medio' => ['label' => 'Médio Ads', 'class_name' => 'is-medium', 'color' => '#b54708'],
        'baixo' => ['label' => 'Baixo Ads', 'class_name' => 'is-low', 'color' => '#175cd3'],
        'sem' => ['label' => 'Sem Avaliação Feita', 'class_name' => 'is-none', 'color' => '#667085'],
    ];

    public function buildScoreBadge(int $score): array
    {
        if ($score >= 8) {
            return ['label' => "Score Digital: {$score}", 'class_name' => 'is-high'];
        }
        if ($score >= 4) {
            return ['label' => "Score Digital: {$score}", 'class_name' => 'is-warm'];
        }
        return ['label' => "Score Digital: {$score}", 'class_name' => 'is-fresh'];
    }

    public function competitorSummary(Collection $queryset): array
    {
        $ctas = $queryset->pluck('cta')->filter()->values()->take(20)->all();
        $categorias = $queryset->pluck('categoria')->filter()->values()->take(20)->all();
        $textos = $queryset->pluck('texto_principal')->filter()->values()->take(10)->all();
        $titulos = $queryset->pluck('titulo')->filter()->values()->take(10)->all();

        $competitors = $this->competitorProfiles($queryset);
        return [
            'total_anuncios' => $queryset->count(),
            'ctas' => $ctas,
            'categorias' => $categorias,
            'amostras_texto' => $textos,
            'amostras_titulo' => $titulos,
            'competitors' => $competitors,
            'observacao_limite' => 'Analise baseada apenas em dados observáveis/importados, sem inferir métricas privadas dos concorrentes.',
        ];
    }

    public function competitorSummaryForNameInPeriod(Collection $queryset, string $competitorName, ?Carbon $periodStart = null, ?Carbon $periodEnd = null): array
    {
        $competitorRows = $queryset->filter(fn ($item) => strcasecmp($item->concorrente_nome, $competitorName) === 0);
        $summary = $this->competitorSummary($competitorRows);
        $profile = collect($summary['competitors'])->first(fn ($item) => strcasecmp($item['nome'], $competitorName) === 0);

        $summary['competidor'] = $profile ?: [
            'nome' => $competitorName,
            'activity_label' => self::ACTIVITY_META['sem']['label'],
            'activity_class' => self::ACTIVITY_META['sem']['class_name'],
            'real_ads_count' => 0,
            'total_registros' => 0,
            'seguidores' => 0,
            'posts_total_publicos' => 0,
            'feed_posts_visiveis' => 0,
            'feed_posts_detalhes' => [],
            'feed_cadencia' => 'Base insuficiente para medir constância',
            'feed_datas_publicadas' => [],
            'feed_formatos' => [],
            'ads_biblioteca_ativo' => false,
            'ads_biblioteca_query' => '',
            'ads_biblioteca_sinal' => 0,
            'ads_biblioteca_consultado_em' => null,
        ];

        $summary['feed_insights'] = [
            'posts_visiveis_periodo' => 0,
            'interacoes_periodo' => 0,
            'comments_periodo' => 0,
            'media_engajamento_por_post' => 0,
            'taxa_atualizacao_label' => 'Base insuficiente para medir constância',
            'formatos_periodo' => [],
        ];
        $summary['feed_insights']['cadencia_total'] = $summary['competidor']['feed_cadencia'] ?? '';
        $summary['feed_insights']['posts_total_publicos'] = $summary['competidor']['posts_total_publicos'] ?? 0;
        return $summary;
    }

    public function competitorProfiles(Collection $queryset): array
    {
        $grouped = [];
        foreach ($queryset as $ad) {
            $name = trim($ad->concorrente_nome ?: 'Concorrente');
            if (!isset($grouped[$name])) {
                $grouped[$name] = ['total_registros' => 0, 'real_ads_count' => 0];
            }
            $grouped[$name]['total_registros'] += 1;
        }
        $profiles = [];
        foreach ($grouped as $name => $data) {
            $activity = $this->classifyCompetitorActivity($data['real_ads_count']);
            $profiles[] = [
                'nome' => $name,
                'activity_label' => $activity['label'],
                'activity_class' => $activity['class_name'],
                'real_ads_count' => $data['real_ads_count'],
                'total_registros' => $data['total_registros'],
                'seguidores' => 0,
                'posts_total_publicos' => 0,
                'feed_posts_visiveis' => 0,
                'feed_posts_detalhes' => [],
                'feed_cadencia' => 'Base insuficiente para medir constância',
                'feed_datas_publicadas' => [],
                'feed_formatos' => [],
                'ads_biblioteca_ativo' => false,
                'ads_biblioteca_query' => '',
                'ads_biblioteca_sinal' => 0,
                'ads_biblioteca_consultado_em' => null,
            ];
        }
        return $profiles;
    }

    public function classifyCompetitorActivity(int $realAdsCount): array
    {
        if ($realAdsCount >= 6) {
            return self::ACTIVITY_META['alto'];
        }
        if ($realAdsCount >= 3) {
            return self::ACTIVITY_META['medio'];
        }
        if ($realAdsCount >= 1) {
            return self::ACTIVITY_META['baixo'];
        }
        return self::ACTIVITY_META['sem'];
    }
}
