<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;

class IaService
{
    private string $apiKey;
    private string $model;

    public function __construct()
    {
        $this->apiKey = (string) config('services.anthropic.key', env('ANTHROPIC_API_KEY', ''));
        $this->model = (string) config('services.anthropic.model', env('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20240620'));
    }

    public function buildAnalysisPayload(array $kpis, array $campaignRows): array
    {
        return [
            'kpis' => [
                'investimento' => (float) ($kpis['investimento'] ?? 0),
                'impressoes' => (int) ($kpis['impressoes'] ?? 0),
                'alcance' => (int) ($kpis['alcance'] ?? 0),
                'cliques' => (int) ($kpis['cliques'] ?? 0),
                'resultados' => (float) ($kpis['resultados'] ?? 0),
                'ctr' => (float) ($kpis['ctr'] ?? 0),
                'cpc' => (float) ($kpis['cpc'] ?? 0),
                'cpm' => (float) ($kpis['cpm'] ?? 0),
                'cpl' => (float) ($kpis['cpl'] ?? 0),
            ],
            'campanhas' => collect($campaignRows)->take(12)->map(fn ($row) => [
                'campanha' => $row['campanha'] ?? '',
                'investimento' => (float) ($row['investimento'] ?? 0),
                'cliques' => (int) ($row['cliques'] ?? 0),
                'ctr' => (float) ($row['ctr'] ?? 0),
                'cpc' => (float) ($row['cpc'] ?? 0),
                'cpm' => (float) ($row['cpm'] ?? 0),
                'resultados' => (float) ($row['resultados'] ?? 0),
                'cpl' => (float) ($row['cpl'] ?? 0),
            ])->values()->all(),
        ];
    }

    public function buildReportPayload(array $kpis, array $campaignRows, array $comparisonRows, array $competitorPayload, string $competitorAnalysisText = '', ?array $companyDigital = null, ?array $competitorRankings = null): array
    {
        $topCompetitors = array_slice($competitorRankings ?? ($competitorPayload['competitors'] ?? []), 0, 3);
        $payload = [
            'kpis' => [
                'investimento' => (float) ($kpis['investimento'] ?? 0),
                'impressoes' => (int) ($kpis['impressoes'] ?? 0),
                'alcance' => (int) ($kpis['alcance'] ?? 0),
                'cliques' => (int) ($kpis['cliques'] ?? 0),
                'resultados' => (float) ($kpis['resultados'] ?? 0),
                'ctr' => (float) ($kpis['ctr'] ?? 0),
                'cpc' => (float) ($kpis['cpc'] ?? 0),
                'cpm' => (float) ($kpis['cpm'] ?? 0),
                'cpl' => (float) ($kpis['cpl'] ?? 0),
            ],
            'campanhas' => collect($campaignRows)->take(10)->map(fn ($row) => [
                'campanha' => $row['campanha'] ?? '',
                'investimento' => (float) ($row['investimento'] ?? 0),
                'impressoes' => (int) ($row['impressoes'] ?? 0),
                'alcance' => (int) ($row['alcance'] ?? 0),
                'cliques' => (int) ($row['cliques'] ?? 0),
                'ctr' => (float) ($row['ctr'] ?? 0),
                'cpc' => (float) ($row['cpc'] ?? 0),
                'cpm' => (float) ($row['cpm'] ?? 0),
                'resultados' => (float) ($row['resultados'] ?? 0),
                'cpl' => (float) ($row['cpl'] ?? 0),
            ])->values()->all(),
            'comparativo' => collect($comparisonRows)->map(fn ($row) => [
                'metrica' => $row['label'] ?? '',
                'atual' => (float) ($row['atual'] ?? 0),
                'anterior' => (float) ($row['anterior'] ?? 0),
                'variacao_absoluta' => (float) ($row['variacao_absoluta'] ?? 0),
                'variacao_percentual' => isset($row['variacao_percentual']) ? (float) $row['variacao_percentual'] : null,
            ])->values()->all(),
            'concorrentes' => [
                'total_anuncios' => (int) ($competitorPayload['total_anuncios'] ?? 0),
                'top_ameacas' => $topCompetitors,
                'ctas' => array_slice($competitorPayload['ctas'] ?? [], 0, 12),
                'categorias' => array_slice($competitorPayload['categorias'] ?? [], 0, 12),
                'analise_concorrencial_salva' => $competitorAnalysisText,
            ],
        ];
        if ($companyDigital) {
            $payload['empresa_digital'] = $companyDigital;
        }
        return $payload;
    }

    public function generateStrategicInsights(array $myDataPayload, array $competitorPayload): string
    {
        $prompt = 'Gere três blocos: 1) resumo executivo dos meus dados, 2) leitura dos concorrentes, 3) comparativo estratégico com hipóteses e testes recomendados para o próximo período. Nunca atribua métricas privadas reais aos concorrentes.';
        return $this->callClaude($prompt, ['meus_dados' => $myDataPayload, 'concorrentes' => $competitorPayload]);
    }

    public function generateCompetitorAnalysis(array $competitorPayload, ?array $companyPayload = null): string
    {
        $payload = $this->buildCompetitorAnalysisPayload($competitorPayload, $companyPayload);
        $competidor = $payload['concorrente'] ?? [];
        $periodo = $competidor['periodo_analisado'] ?? [];
        $ads = $competidor['ads_meta_ads_library'] ?? [];
        $facts = "FATOS OBRIGATÓRIOS PARA USAR NO TEXTO:\n"
            . "- Feed no período: " . ($periodo['feed_no_periodo'] ?? 0) . "\n"
            . "- Interações no período: " . ($periodo['interacoes_no_periodo'] ?? 0) . "\n"
            . "- Comentários no período: " . ($periodo['comentarios_no_periodo'] ?? 0) . "\n"
            . "- Média de engajamento por post: " . ($periodo['media_engajamento_por_post'] ?? 0) . "\n"
            . "- Taxa de atualização: " . ($periodo['taxa_atualizacao'] ?? '') . "\n"
            . "- Ads ativos na Meta Ads Library: " . ($ads['ativos_encontrados'] ?? 0) . "\n"
            . "Esses números são a verdade do recorte. Não substitua, não reconte e não arredonde para outro total.\n";

        $prompt = 'Analise apenas os dados observáveis/importados do concorrente informado, respeitando o recorte de período enviado, e gere uma leitura subjetiva e estratégica. '
            . 'Use como fonte principal os campos do período em feed_insights, especialmente posts_visiveis_periodo, interacoes_periodo, comments_periodo, media_engajamento_por_post e taxa_atualizacao_label. '
            . 'Se houver dados da empresa analisada em empresa_digital, compare explicitamente o concorrente com a empresa em termos de constância, presença no feed, engajamento observável e sinal de ads ativos. '
            . 'Aponte onde o concorrente está acima, empatado ou abaixo da empresa, sem inventar dados. '
            . 'Considere como valor oficial do recorte apenas concorrente.periodo_analisado.feed_no_periodo. '
            . 'Nunca cite contagens, interações ou comentários que não estejam explicitamente dentro de concorrente.periodo_analisado. '
            . 'Se for mencionar feed, interações, comentários ou média por post, use exatamente os números presentes em concorrente.periodo_analisado. '
            . 'Se concorrente.ads_meta_ads_library.ativos_encontrados for maior que zero, trate isso como evidência pública de anúncios ativos na Meta Ads Library e cite isso com objetividade. '
            . 'Se concorrente.ads_meta_ads_library.ativos_encontrados for zero, diga que nao houve sinal público de ads ativos na Meta Ads Library no momento da consulta. '
            . 'Repita taxa_atualizacao exatamente como veio em concorrente.periodo_analisado.taxa_atualizacao. '
            . 'Se houver 4 posts ou menos no período, nao descreva a presença como forte, notável, robusta ou dominante; trate como presença limitada ou moderada. '
            . $facts;

        return $this->callClaude($prompt, $payload);
    }

    public function buildCompetitorAnalysisPayload(array $competitorPayload, ?array $companyPayload = null): array
    {
        $competitor = $competitorPayload['competidor'] ?? [];
        $feed = $competitorPayload['feed_insights'] ?? [];
        $payload = [
            'concorrente' => [
                'nome' => $competitor['nome'] ?? '',
                'status_ads' => $competitor['activity_label'] ?? '',
                'ads_meta_ads_library' => [
                    'ativos_encontrados' => (int) ($competitor['ads_biblioteca_sinal'] ?? 0),
                    'busca_utilizada' => $competitor['ads_biblioteca_query'] ?? '',
                    'consultado_em' => $competitor['ads_biblioteca_consultado_em'] ?? null,
                ],
                'periodo_analisado' => [
                    'feed_no_periodo' => (int) ($feed['posts_visiveis_periodo'] ?? 0),
                    'interacoes_no_periodo' => (int) ($feed['interacoes_periodo'] ?? 0),
                    'comentarios_no_periodo' => (int) ($feed['comments_periodo'] ?? 0),
                    'media_engajamento_por_post' => (float) ($feed['media_engajamento_por_post'] ?? 0),
                    'taxa_atualizacao' => $feed['taxa_atualizacao_label'] ?? '',
                    'formatos_no_periodo' => $feed['formatos_periodo'] ?? [],
                ],
            ],
        ];
        if ($companyPayload) {
            $companyFeed = $companyPayload['feed_insights'] ?? [];
            $payload['empresa_digital'] = [
                'nome' => $companyPayload['nome'] ?? '',
                'ads_meta_ads_library' => [
                    'ativos_encontrados' => (int) ($companyPayload['ads_biblioteca_sinal'] ?? 0),
                    'busca_utilizada' => $companyPayload['ads_biblioteca_query'] ?? '',
                ],
                'periodo_analisado' => [
                    'feed_no_periodo' => (int) ($companyFeed['posts_visiveis_periodo'] ?? 0),
                    'interacoes_no_periodo' => (int) ($companyFeed['interacoes_periodo'] ?? 0),
                    'comentarios_no_periodo' => (int) ($companyFeed['comments_periodo'] ?? 0),
                    'media_engajamento_por_post' => (float) ($companyFeed['media_engajamento_por_post'] ?? 0),
                    'taxa_atualizacao' => $companyFeed['taxa_atualizacao_label'] ?? '',
                ],
            ];
        }
        return $payload;
    }

    public function callClaude(string $prompt, array $payload): string
    {
        if (!$this->apiKey) {
            return 'ANTHROPIC_API_KEY não configurada. A análise de IA foi pulada.';
        }
        $response = Http::timeout(60)->withHeaders([
            'x-api-key' => $this->apiKey,
            'anthropic-version' => '2023-06-01',
        ])->post('https://api.anthropic.com/v1/messages', [
            'model' => $this->model,
            'max_tokens' => 1200,
            'messages' => [
                [
                    'role' => 'user',
                    'content' => $prompt . "\n\nDados estruturados:\n" . json_encode($payload, JSON_UNESCAPED_UNICODE),
                ],
            ],
        ]);
        if (!$response->ok()) {
            return 'Falha ao consultar o serviço de IA.';
        }
        $data = $response->json();
        return $data['content'][0]['text'] ?? 'Resposta vazia da IA.';
    }
}
