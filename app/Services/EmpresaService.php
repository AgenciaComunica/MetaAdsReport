<?php

namespace App\Services;

use App\Models\Empresa;
use Carbon\Carbon;

class EmpresaService
{
    public const LEGACY_DIGITAL_NOTE_MARKERS = [
        'Instagram da empresa:',
        'Meta Ads Library:',
        'Busca usada:',
        'Ads ativos encontrados:',
    ];

    public function stripEmpresaLegacyDigitalNotes(?string $text): string
    {
        $rawText = trim((string) $text);
        if ($rawText === '') {
            return '';
        }
        $cleaned = [];
        foreach (preg_split('/\r\n|\r|\n/', $rawText) as $line) {
            $normalized = trim($line);
            if ($normalized === '') {
                if (!empty($cleaned) && trim(end($cleaned)) !== '') {
                    $cleaned[] = '';
                }
                continue;
            }
            $skip = false;
            foreach (self::LEGACY_DIGITAL_NOTE_MARKERS as $marker) {
                if (str_starts_with($normalized, $marker)) {
                    $skip = true;
                    break;
                }
            }
            if ($skip) {
                continue;
            }
            $cleaned[] = $line;
        }
        while (!empty($cleaned) && trim(end($cleaned)) === '') {
            array_pop($cleaned);
        }
        return trim(implode("\n", $cleaned));
    }

    public function socialLinksToTextarea(array|string|null $socialLinks): string
    {
        if (is_string($socialLinks)) {
            return trim($socialLinks);
        }

        if (!is_array($socialLinks) || empty($socialLinks)) {
            return '';
        }

        $lines = [];
        foreach ($socialLinks as $item) {
            if (is_array($item)) {
                $network = trim((string) ($item['rede'] ?? ''));
                $url = trim((string) ($item['url'] ?? ''));
                if ($network !== '' && $url !== '') {
                    $lines[] = $network . ' | ' . $url;
                    continue;
                }
                if ($url !== '') {
                    $lines[] = $url;
                    continue;
                }
            }

            $value = trim((string) $item);
            if ($value !== '') {
                $lines[] = $value;
            }
        }

        return implode("\n", $lines);
    }

    public function socialLinksFromTextarea(?string $text): array
    {
        $raw = trim((string) $text);
        if ($raw === '') {
            return [];
        }

        $items = [];
        foreach (preg_split('/\r\n|\r|\n/', $raw) as $line) {
            $value = trim($line);
            if ($value === '') {
                continue;
            }

            if (str_contains($value, '|')) {
                [$network, $url] = array_pad(array_map('trim', explode('|', $value, 2)), 2, '');
                $items[] = [
                    'rede' => $network,
                    'url' => $url,
                ];
                continue;
            }

            $items[] = $value;
        }

        return $items;
    }

    public function refreshEmpresaProfileRecord(Empresa $empresa): array
    {
        $empresa->observacoes = $this->stripEmpresaLegacyDigitalNotes($empresa->observacoes);
        $empresa->save();
        return [$empresa, ['Leitura externa de Instagram não implementada no Laravel ainda.']];
    }

    public function empresaDigitalSummary(Empresa $empresa, ?Carbon $periodStart = null, ?Carbon $periodEnd = null): array
    {
        return [
            'nome' => $empresa->nome,
            'instagram_profile_url' => $empresa->instagram_profile_url,
            'ads_biblioteca_ativo' => $empresa->ads_biblioteca_ativo,
            'ads_biblioteca_query' => $empresa->ads_biblioteca_query,
            'ads_biblioteca_sinal' => $empresa->ads_biblioteca_sinal,
            'ads_biblioteca_consultado_em' => $empresa->ads_biblioteca_consultado_em,
            'seguidores' => $empresa->seguidores,
            'posts_total_publicos' => $empresa->posts_total_publicos,
            'feed_posts_visiveis' => $empresa->feed_posts_visiveis,
            'feed_cadencia' => $empresa->feed_cadencia,
            'feed_formatos' => $empresa->feed_formatos ?: [],
            'feed_insights' => [
                'digital_score' => 0,
                'digital_score_label' => 'Score Digital: 0',
                'digital_score_class' => 'is-fresh',
                'posts_visiveis_periodo' => 0,
                'interacoes_periodo' => 0,
                'comments_periodo' => 0,
                'media_engajamento_por_post' => 0,
                'taxa_atualizacao_label' => 'Base insuficiente para medir constância',
                'formatos_periodo' => [],
            ],
            'digital_score_label' => 'Score Digital: 0',
            'digital_score_class' => 'is-fresh',
        ];
    }
}
