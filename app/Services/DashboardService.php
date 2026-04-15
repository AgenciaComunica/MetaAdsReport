<?php

namespace App\Services;

use App\Models\CampanhaMetric;
use App\Models\ConcorrenteAd;
use App\Models\ConfiguracaoUploadEmpresa;
use App\Models\Empresa;
use App\Models\EventoPainel;
use App\Models\Relatorio;
use App\Models\UploadCampanha;
use App\Models\UploadPainel;
use Carbon\Carbon;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class DashboardService
{
    private const TRAFEGO_PAGO = 'trafego_pago';
    private const CRM_VENDAS = 'crm_vendas';
    private const LEADS_EVENTOS = 'leads_eventos';
    private const REDES_SOCIAIS = 'redes_sociais';

    private const PAID_TRAFFIC_HINTS = ['meta', 'facebook', 'instagram', 'ads', 'trafego', 'tráfego'];

    private const TRAFFIC_BLOCK_DEFINITIONS = [
        [
            'key' => 'resultados',
            'title' => 'Resultados',
            'description' => 'Bloco principal de conversão, preparado para múltiplas plataformas e objetivos.',
            'metrics' => ['resultado_principal', 'custo_por_resultado', 'taxa_resposta'],
            'chart_metrics' => ['resultado_principal'],
            'highlighted' => true,
        ],
        [
            'key' => 'custo_investimento',
            'title' => 'Custo e Investimento',
            'description' => 'Controle financeiro do período e eficiência básica do investimento.',
            'metrics' => ['investimento', 'cpm', 'cpc', 'cpl'],
            'chart_metrics' => ['investimento'],
            'highlighted' => false,
        ],
        [
            'key' => 'performance_anuncios',
            'title' => 'Performance dos Anúncios',
            'description' => 'Entrega, alcance e capacidade de gerar ação ao longo do funil.',
            'metrics' => ['impressoes', 'alcance', 'ctr', 'taxa_conversao', 'frequencia'],
            'chart_metrics' => ['impressoes', 'alcance'],
            'highlighted' => false,
        ],
        [
            'key' => 'qualidade_relevancia',
            'title' => 'Qualidade e Relevância',
            'description' => 'Leitura sintética da saúde do criativo e da pressão de mídia.',
            'metrics' => ['score_relevancia', 'cpm_relativo'],
            'chart_metrics' => ['score_relevancia'],
            'highlighted' => false,
        ],
    ];

    private const TRAFFIC_METRIC_TOOLTIPS = [
        'investimento' => 'Valor total investido em mídia no período selecionado.',
        'cpm' => 'Custo médio para cada mil impressões entregues.',
        'cpc' => 'Custo médio por clique gerado pelos anúncios.',
        'cpl' => 'Custo por lead ou custo por resultado principal captado.',
        'impressoes' => 'Quantidade total de exibições dos anúncios.',
        'alcance' => 'Quantidade de pessoas únicas alcançadas.',
        'ctr' => 'Percentual de cliques em relação às impressões.',
        'taxa_conversao' => 'Percentual de resultados em relação aos cliques.',
        'frequencia' => 'Média de vezes que cada pessoa impactada viu o anúncio.',
        'score_relevancia' => 'Indicador sintético calculado com base em CTR, CPM, CPC e frequência.',
        'cpm_relativo' => 'Compara o CPM atual com o período anterior. Abaixo de 1,00x é melhor.',
        'resultado_principal' => 'Conversão principal do painel, genérica e preparada para diferentes objetivos.',
        'custo_por_resultado' => 'Custo médio por conversão principal obtida.',
        'taxa_resposta' => 'Percentual de respostas ou conversões em relação aos cliques gerados.',
    ];

    private const CRM_STATUS_COLOR_MAP = [
        'venda concluida' => '#2d6a4f',
        'venda concluída' => '#2d6a4f',
        'retorno' => '#175cd3',
        'ausência de resposta' => '#6b7280',
        'ausencia de resposta' => '#6b7280',
        'pedido com +10 peças' => '#0f766e',
        'conhecimento com preço menor' => '#f59e0b',
        'cliente indeciso' => '#7c3aed',
        'indisponibilidade de data' => '#0ea5e9',
        'apenas passar valores' => '#f97316',
        'demora no atendimento' => '#dc2626',
        'fora do escopo' => '#92400e',
        'relação 0 - sem venda' => '#475569',
        'falta de identificação da necessidade no interesse' => '#b45309',
        'interação interna' => '#4f46e5',
        'não informado' => '#94a3b8',
    ];

    private const CRM_STATUS_COLOR_RULES = [
        ['venda concluida', '#16A34A'],
        ['retorno', '#2563EB'],
        ['ausencia de resposta', '#9CA3AF'],
        ['pedido com', '#F97316'],
        ['nao aprovou o valor', '#DC2626'],
        ['concorrente com preco menor', '#7C3AED'],
        ['cliente indeciso', '#FACC15'],
        ['indisponibilidade de data', '#0ea5e9'],
        ['apenas saber valores', '#14B8A6'],
        ['demora no atendimento', '#FB7185'],
        ['fora do escopo', '#A855F7'],
        ['reacao ig', '#A855F7'],
        ['recusa de identificacao da marca clone', '#D97706'],
        ['interacao interna', '#334155'],
        ['nao informado', '#94a3b8'],
    ];

    private const LEAD_TEMPERATURE_COLOR_RULES = [
        ['cliente', '#16A34A'],
        ['muito quente', '#A855F7'],
        ['quente', '#DC2626'],
        ['frio', '#2563EB'],
        ['nao informado', '#94A3B8'],
    ];

    private const LEAD_TEMPERATURE_DISPLAY_ORDER = ['Cliente', 'Muito Quente', 'Quente', 'Frio', 'Não informado'];

    public function __construct(
        private readonly CampanhaService $campanhaService,
        private readonly ConcorrenteService $concorrenteService,
    ) {
    }

    public function build(?Empresa $empresa, string $dashboardTab = '', string $mesParam = ''): array
    {
        $ranges = $mesParam
            ? $this->campanhaService->monthRangesForParam($mesParam)
            : $this->campanhaService->lastCompleteMonthRanges();

        $currentStart = $ranges['current_start'];
        $currentEnd = $ranges['current_end'];
        $previousStart = $ranges['previous_start'];
        $previousEnd = $ranges['previous_end'];
        $mesParam = $mesParam ?: $currentStart->format('Y-m');
        $selectedMonth = (int) $currentStart->format('n');
        $selectedYear = (int) $currentStart->format('Y');
        $availableYears = collect($this->campanhaService->availableMonths())
            ->map(fn (array $item) => (int) substr((string) $item['value'], 0, 4))
            ->unique()
            ->sortDesc()
            ->values()
            ->all();
        $availableMonths = [
            ['value' => 1, 'label' => 'Janeiro'],
            ['value' => 2, 'label' => 'Fevereiro'],
            ['value' => 3, 'label' => 'Março'],
            ['value' => 4, 'label' => 'Abril'],
            ['value' => 5, 'label' => 'Maio'],
            ['value' => 6, 'label' => 'Junho'],
            ['value' => 7, 'label' => 'Julho'],
            ['value' => 8, 'label' => 'Agosto'],
            ['value' => 9, 'label' => 'Setembro'],
            ['value' => 10, 'label' => 'Outubro'],
            ['value' => 11, 'label' => 'Novembro'],
            ['value' => 12, 'label' => 'Dezembro'],
        ];

        $empresa?->loadMissing([
            'configuracoes_upload.uploads_painel',
            'configuracoes_upload.eventos_painel',
        ]);

        $currentMetrics = $empresa
            ? $this->campanhaService->metricsQuery($empresa->id, $currentStart, $currentEnd)->get()
            : collect();
        $previousMetrics = $empresa
            ? $this->campanhaService->metricsQuery($empresa->id, $previousStart, $previousEnd)->get()
            : collect();

        $trafficConfig = $empresa?->configuracoes_upload->firstWhere('tipo_documento', self::TRAFEGO_PAGO);
        $crmConfigs = $empresa?->configuracoes_upload->where('tipo_documento', self::CRM_VENDAS)->values() ?? collect();
        $socialConfigs = $empresa?->configuracoes_upload->where('tipo_documento', self::REDES_SOCIAIS)->values() ?? collect();
        $leadsConfigs = $empresa?->configuracoes_upload->where('tipo_documento', self::LEADS_EVENTOS)->values() ?? collect();

        $visibleTabs = collect();

        if ($empresa && $empresa->configuracoes_upload->isNotEmpty()) {
            $visibleTabs->push(['key' => 'analise_completa', 'title' => 'Resumo Executivo']);
        }

        foreach ($empresa?->configuracoes_upload ?? [] as $config) {
            $visibleTabs->push([
                'key' => $this->configTabKey($config),
                'title' => $config->nome,
            ]);
        }

        $visibleTabs->push(['key' => 'concorrentes', 'title' => 'Concorrentes']);

        $dashboardTab = $dashboardTab ?: ($visibleTabs->first()['key'] ?? 'concorrentes');

        $activeConfig = $empresa?->configuracoes_upload->first(
            fn (ConfiguracaoUploadEmpresa $config) => $this->configTabKey($config) === $dashboardTab
        );

        $trafficTab = $trafficConfig
            ? $this->buildTrafficTab($trafficConfig, $currentMetrics, $previousMetrics)
            : null;

        $activeUploadTab = null;
        if ($activeConfig) {
            $activeUploadTab = match ($activeConfig->tipo_documento) {
                self::TRAFEGO_PAGO => $trafficTab,
                self::CRM_VENDAS => $this->buildCrmTab($activeConfig, $currentStart, $currentEnd, $previousStart, $previousEnd),
                self::LEADS_EVENTOS => $this->buildLeadsTab($activeConfig, $currentStart, $currentEnd),
                self::REDES_SOCIAIS => $this->buildSocialTab($activeConfig, $currentStart, $currentEnd, $previousStart, $previousEnd),
                default => null,
            };
        }

        $analiseCompletaTab = $dashboardTab === 'analise_completa'
            ? $this->buildExecutiveTab($empresa, $currentMetrics, $previousMetrics, $trafficConfig, $crmConfigs, $socialConfigs, $leadsConfigs, $currentStart, $currentEnd, $previousStart, $previousEnd)
            : null;

        $concorrentesTab = $dashboardTab === 'concorrentes'
            ? $this->buildCompetitorsTab($empresa, $currentStart, $currentEnd)
            : null;

        $uploadsList = $empresa
            ? UploadCampanha::query()
                ->where('empresa_id', $empresa->id)
                ->orderByDesc('created_at')
                ->limit(10)
                ->get()
            : collect();

        $panelUploadsList = $activeConfig
            ? UploadPainel::query()->where('configuracao_id', $activeConfig->id)->orderByDesc('created_at')->get()
            : collect();

        $eventosPainelList = $activeConfig && $activeConfig->tipo_documento === self::LEADS_EVENTOS
            ? EventoPainel::query()->where('configuracao_id', $activeConfig->id)->orderByDesc('data_evento')->get()
            : collect();

        $relatoriosList = $empresa
            ? Relatorio::query()->where('empresa_id', $empresa->id)->orderByDesc('created_at')->limit(10)->get()
            : collect();

        return [
            'empresa' => $empresa,
            'dashboard_tab' => $dashboardTab,
            'visible_dashboard_tabs' => $visibleTabs->values()->all(),
            'active_upload_tab' => $activeUploadTab,
            'analise_completa_tab' => $analiseCompletaTab,
            'concorrentes_tab' => $concorrentesTab,
            'mes_param' => $mesParam,
            'selected_month' => $selectedMonth,
            'selected_year' => $selectedYear,
            'available_months' => $availableMonths,
            'available_years' => $availableYears,
            'periodo_anterior_resumo' => $previousStart->translatedFormat('F/Y'),
            'periodo_atual_resumo' => $currentStart->format('d/m/Y').' - '.$currentEnd->format('d/m/Y'),
            'current_start' => $currentStart,
            'current_end' => $currentEnd,
            'previous_start' => $previousStart,
            'previous_end' => $previousEnd,
            'current_start_iso' => $currentStart->toDateString(),
            'current_end_iso' => $currentEnd->toDateString(),
            'previous_start_iso' => $previousStart->toDateString(),
            'previous_end_iso' => $previousEnd->toDateString(),
            'mes_label' => ucfirst($currentStart->translatedFormat('F/Y')),
            'previous_month_label' => ucfirst($previousStart->translatedFormat('F/Y')),
            'campaign_rows' => $trafficTab['campaign_rows'] ?? $this->campanhaService->campaignTable($currentMetrics),
            'uploads_list' => $uploadsList,
            'panel_uploads_list' => $panelUploadsList,
            'eventos_painel_list' => $eventosPainelList,
            'relatorios_list' => $relatoriosList,
            'traffic_has_data' => $currentMetrics->isNotEmpty(),
        ];
    }

    private function buildTrafficTab(
        ConfiguracaoUploadEmpresa $config,
        Collection $currentMetrics,
        Collection $previousMetrics,
    ): array {
        $summary = $this->campanhaService->summarizeMetrics($currentMetrics);
        $previousSummary = $this->campanhaService->summarizeMetrics($previousMetrics);
        $resultLabel = $this->resolveResultLabel($config);
        $metricDefinitions = $this->buildTrafficMetricDefinitions($resultLabel);
        $metricValues = $this->buildTrafficMetricValues($summary, $previousSummary);
        $previousMetricValues = $this->buildTrafficMetricValues($previousSummary, []);
        $selectedTableKeys = $this->enabledTableMetricKeys(self::TRAFEGO_PAGO, $config->metricas_painel_json);
        $selectedChartKeys = $this->enabledChartMetricKeys(self::TRAFEGO_PAGO, $config->metricas_painel_json);
        $filterEnabledMap = $this->categoryFilterEnabledMap(self::TRAFEGO_PAGO, $config->metricas_painel_json);
        $metricBlocks = $this->buildTrafficBlocks($metricValues, $previousMetricValues, $metricDefinitions, $selectedTableKeys, $filterEnabledMap);

        $chartKeys = [];
        foreach (self::TRAFFIC_BLOCK_DEFINITIONS as $block) {
            $keys = array_values(array_intersect($block['chart_metrics'], $selectedChartKeys));
            if ($keys === []) {
                $keys = array_values(array_intersect($block['chart_metrics'], $selectedTableKeys));
            }
            foreach ($keys as $key) {
                if (! in_array($key, $chartKeys, true)) {
                    $chartKeys[] = $key;
                }
            }
        }

        return [
            'key' => $this->configTabKey($config),
            'panel_type' => self::TRAFEGO_PAGO,
            'title' => $config->nome,
            'config_id' => $config->id,
            'configured' => true,
            'ready' => $currentMetrics->isNotEmpty(),
            'config_name' => $config->nome,
            'description' => 'Painel escalável para mídia paga, com foco em eficiência, qualidade e conversão.',
            'kpis' => $summary,
            'result_label' => $resultLabel,
            'metric_blocks' => $metricBlocks,
            'tab_chart' => $this->buildTrafficLineChart($config->empresa_id, $chartKeys, $metricDefinitions),
            'campaign_rows' => $this->campanhaService->campaignTable($currentMetrics),
        ];
    }

    private function buildCrmTab(
        ConfiguracaoUploadEmpresa $config,
        Carbon $periodStart,
        Carbon $periodEnd,
        Carbon $previousStart,
        Carbon $previousEnd,
    ): array {
        $allRows = $this->readMappedRows($config);
        $rows = $this->filterRowsByPeriod($allRows, $periodStart, $periodEnd, 'data_contato');
        $previousRows = $this->filterRowsByPeriod($allRows, $previousStart, $previousEnd, 'data_contato');
        $closedStatus = ['ganho', 'fechado', 'fechada', 'venda', 'vendido'];
        $currentSummary = $this->crmPeriodSummary($rows, $closedStatus, $config);
        $previousSummary = $this->crmPeriodSummary($previousRows, $closedStatus, $config);

        return [
            'key' => $this->configTabKey($config),
            'panel_type' => self::CRM_VENDAS,
            'title' => $config->nome,
            'config_id' => $config->id,
            'configured' => true,
            'ready' => filled($config->mapeamento_json),
            'config_name' => $config->nome,
            'description' => 'Leitura do arquivo configurado para CRM e vendas.',
            'rows' => array_slice($rows, 0, 20),
            'kpis' => $currentSummary['geral'],
            'tab_chart' => $this->buildOrigemStackedAreaChart($allRows, $config),
            'category_blocks' => $this->buildCrmCategoryBlocks(
                $this->enabledTableMetricKeys(self::CRM_VENDAS, $config->metricas_painel_json),
                $this->enabledChartMetricKeys(self::CRM_VENDAS, $config->metricas_painel_json),
                $currentSummary,
                $previousSummary,
                $this->categoryFilterEnabledMap(self::CRM_VENDAS, $config->metricas_painel_json),
            ),
        ];
    }

    private function buildLeadsTab(
        ConfiguracaoUploadEmpresa $config,
        Carbon $periodStart,
        Carbon $periodEnd,
    ): array {
        $rows = [];
        $entries = [];

        foreach ($config->eventos_painel as $entry) {
            if ($entry->data_evento < $periodStart || $entry->data_evento > $periodEnd) {
                continue;
            }

            $entries[] = $entry;
            $rows[] = [
                'evento' => $entry->nome_evento,
                'data_evento' => $entry->data_evento,
                'impacto' => $this->eventoImpactoLabel($entry->impacto),
                'leads_media' => $entry->leads_media,
            ];
        }

        return [
            'key' => $this->configTabKey($config),
            'panel_type' => self::LEADS_EVENTOS,
            'title' => $config->nome,
            'config_id' => $config->id,
            'configured' => true,
            'ready' => true,
            'config_name' => $config->nome,
            'description' => 'Entradas manuais de eventos com impacto e média de pessoas alcançadas.',
            'rows' => array_slice($rows, 0, 50),
            'kpis' => [
                'eventos_total' => count($entries),
                'participantes_total' => collect($entries)->sum('leads_media'),
            ],
            'tab_chart' => $this->buildLeadsMonthlyLineChart($config),
        ];
    }

    private function buildSocialTab(
        ConfiguracaoUploadEmpresa $config,
        Carbon $periodStart,
        Carbon $periodEnd,
        Carbon $previousStart,
        Carbon $previousEnd,
    ): array {
        $digitalType = $this->getSocialDigitalType($config);
        $allRows = $this->readSocialRows($config);
        $rows = $this->filterRowsByPeriod($allRows, $periodStart, $periodEnd, 'data_publicacao');
        $previousRows = $this->filterRowsByPeriod($allRows, $previousStart, $previousEnd, 'data_publicacao');
        $currentSummary = $this->socialPeriodSummary($rows, $digitalType);
        $previousSummary = $this->socialPeriodSummary($previousRows, $digitalType);
        $tableKeys = $this->enabledTableMetricKeys(self::REDES_SOCIAIS, $config->metricas_painel_json, $digitalType);
        $chartKeys = $this->enabledChartMetricKeys(self::REDES_SOCIAIS, $config->metricas_painel_json, $digitalType);

        $definitions = $this->socialBlockDefinitions($digitalType);
        $overviewDefinition = collect($definitions)->firstWhere('key', 'visao_geral');
        $combinedChartKeys = [];
        $metricDefs = [];

        if (is_array($overviewDefinition)) {
            $combinedChartKeys = array_values(array_intersect($overviewDefinition['chart_metrics'], $chartKeys));
            foreach ($overviewDefinition['metrics'] as $metricDef) {
                if (in_array($metricDef['key'], $combinedChartKeys, true)) {
                    $metricDefs[$metricDef['key']] = $metricDef;
                }
            }
        }

        return [
            'key' => $this->configTabKey($config),
            'panel_type' => self::REDES_SOCIAIS,
            'title' => $config->nome,
            'config_id' => $config->id,
            'configured' => true,
            'ready' => true,
            'config_name' => $config->nome,
            'description' => $this->socialTabDescription($digitalType),
            'rows' => array_slice($rows, 0, 20),
            'tab_chart' => $this->buildSocialMonthlyLineChart($allRows, $digitalType, array_values($metricDefs), $combinedChartKeys),
            'category_blocks' => $this->buildSocialCategoryBlocks(
                $digitalType,
                $tableKeys,
                $currentSummary,
                $previousSummary,
                $this->categoryFilterEnabledMap(self::REDES_SOCIAIS, $config->metricas_painel_json, $digitalType),
            ),
        ];
    }

    private function buildExecutiveTab(
        ?Empresa $empresa,
        Collection $currentMetrics,
        Collection $previousMetrics,
        ?ConfiguracaoUploadEmpresa $trafficConfig,
        Collection $crmConfigs,
        Collection $socialConfigs,
        Collection $leadsConfigs,
        Carbon $currentStart,
        Carbon $currentEnd,
        Carbon $previousStart,
        Carbon $previousEnd,
    ): array {
        $crmConfig = $crmConfigs->first();
        $trafficSummary = $this->campanhaService->summarizeMetrics($currentMetrics);
        $previousTrafficSummary = $this->campanhaService->summarizeMetrics($previousMetrics);

        $crmRows = $crmConfig ? $this->filterRowsByPeriod($this->readMappedRows($crmConfig), $currentStart, $currentEnd, 'data_contato') : [];
        $previousCrmRows = $crmConfig ? $this->filterRowsByPeriod($this->readMappedRows($crmConfig), $previousStart, $previousEnd, 'data_contato') : [];
        $crmSummary = $this->crmPeriodSummary($crmRows, ['ganho', 'fechado', 'fechada', 'venda', 'vendido'], $crmConfig);
        $previousCrmSummary = $this->crmPeriodSummary($previousCrmRows, ['ganho', 'fechado', 'fechada', 'venda', 'vendido'], $crmConfig);

        $socialSummaries = [];
        $previousSocialSummaries = [];
        foreach ($socialConfigs as $config) {
            $type = $this->getSocialDigitalType($config);
            $allRows = $this->readSocialRows($config);
            $socialSummaries[] = $this->socialPeriodSummary($this->filterRowsByPeriod($allRows, $currentStart, $currentEnd, 'data_publicacao'), $type);
            $previousSocialSummaries[] = $this->socialPeriodSummary($this->filterRowsByPeriod($allRows, $previousStart, $previousEnd, 'data_publicacao'), $type);
        }
        $socialSummary = $this->aggregateSocialSummaries($socialSummaries);
        $previousSocialSummary = $this->aggregateSocialSummaries($previousSocialSummaries);

        $leadsEntries = [];
        $previousLeadsEntries = [];
        foreach ($leadsConfigs as $config) {
            $leadsEntries = [...$leadsEntries, ...$this->filterLeadsEntries($config, $currentStart, $currentEnd)];
            $previousLeadsEntries = [...$previousLeadsEntries, ...$this->filterLeadsEntries($config, $previousStart, $previousEnd)];
        }

        $marketingRows = array_values(array_filter($crmRows, fn (array $row) => $this->isMarketingSale($row, $crmConfig)));
        $previousMarketingRows = array_values(array_filter($previousCrmRows, fn (array $row) => $this->isMarketingSale($row, $crmConfig)));
        $operacaoRows = array_values(array_filter($crmRows, fn (array $row) => $this->isOperacaoOrSemCategoriaSale($row, $crmConfig)));
        $previousOperacaoRows = array_values(array_filter($previousCrmRows, fn (array $row) => $this->isOperacaoOrSemCategoriaSale($row, $crmConfig)));

        $marketingRevenue = collect($marketingRows)->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0));
        $previousMarketingRevenue = collect($previousMarketingRows)->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0));
        $operacaoRevenue = collect($operacaoRows)->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0));
        $previousOperacaoRevenue = collect($previousOperacaoRows)->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0));

        $marketingRevenue += $operacaoRevenue * $this->combinedMarketingShare($socialConfigs, $socialSummaries, $leadsConfigs, $leadsEntries);
        $previousMarketingRevenue += $previousOperacaoRevenue * $this->combinedMarketingShare($socialConfigs, $previousSocialSummaries, $leadsConfigs, $previousLeadsEntries);

        return [
            'key' => 'analise_completa',
            'panel_type' => 'analise_completa',
            'title' => 'Resumo Executivo',
            'configured' => true,
            'ready' => $empresa !== null,
            'description' => 'Painel cruzado geral entre presença digital, atendimento e resultado.',
            'tab_chart' => $this->buildExecutiveChart($empresa, $crmConfig, $socialConfigs, $leadsConfigs),
            'top_cards' => [
                [
                    'label' => 'Receita Marketing Consolidado',
                    'value' => br_currency($marketingRevenue),
                    'tooltip' => 'Soma de tráfego pago, receita direta de marketing e participação operacional atribuída ao marketing.',
                ],
                [
                    'label' => 'Alcance Físico',
                    'value' => br_number(collect($leadsEntries)->sum('leads_media'), 0),
                    'tooltip' => 'Pessoas alcançadas nos eventos presenciais cadastrados.',
                ],
                [
                    'label' => 'Taxa de Conversão',
                    'value' => br_number($crmSummary['geral']['taxa_conversao'] ?? 0, 2).'%',
                    'tooltip' => 'Conversão geral do CRM no período atual.',
                ],
                [
                    'label' => 'Alcance Digital',
                    'value' => br_number(($socialSummary['alcance'] ?? 0), 0),
                    'tooltip' => 'Alcance consolidado dos painéis de Presença Digital no período.',
                ],
            ],
            'summary_panels' => [
                $this->buildSummaryPanel('presenca_digital', 'Presença Digital', 'Soma de presença digital com tráfego pago para leitura consolidada de alcance digital.', [
                    ['presenca_digital_visualizacoes_totais', 'Visualizações Totais', ($previousTrafficSummary['impressoes'] ?? 0) + ($previousSocialSummary['visualizacoes'] ?? 0), ($trafficSummary['impressoes'] ?? 0) + ($socialSummary['visualizacoes'] ?? 0), false, ''],
                    ['presenca_digital_alcance_total', 'Alcance Total', ($previousSocialSummary['alcance'] ?? 0), ($socialSummary['alcance'] ?? 0), false, ''],
                    ['presenca_digital_visualizacoes_redes', 'Visualizações de Redes', $previousSocialSummary['visualizacoes'] ?? 0, $socialSummary['visualizacoes'] ?? 0, false, ''],
                    ['presenca_digital_impressoes_trafego', 'Impressões de Tráfego', $previousTrafficSummary['impressoes'] ?? 0, $trafficSummary['impressoes'] ?? 0, false, ''],
                ]),
                $this->buildSummaryPanel('presenca_fisica', 'Presença Física', 'Leads e ações com presença física.', [
                    ['presenca_fisica_leads_presenciais', 'Leads com Ação Presencial', collect($previousLeadsEntries)->sum('leads_media'), collect($leadsEntries)->sum('leads_media'), false, ''],
                    ['presenca_fisica_oportunidades_presenciais', 'Eventos no Período', count($previousLeadsEntries), count($leadsEntries), false, ''],
                ]),
                $this->buildSummaryPanel('atendimento', 'Atendimento', 'Conversas iniciadas por origem e taxa de conversão do atendimento.', [
                    ['atendimento_conversas_trafego_pago', 'Conversas Tráfego Pago', $previousCrmSummary['origem']['trafego_pago_conversas'] ?? 0, $crmSummary['origem']['trafego_pago_conversas'] ?? 0, false, ''],
                    ['atendimento_conversas_organicas', 'Conversas Orgânicas', $previousCrmSummary['origem']['organico_conversas'] ?? 0, $crmSummary['origem']['organico_conversas'] ?? 0, false, ''],
                    ['atendimento_taxa_conversao', 'Taxa de Conversão', $previousCrmSummary['geral']['taxa_conversao'] ?? 0, $crmSummary['geral']['taxa_conversao'] ?? 0, false, '%'],
                ]),
                $this->buildSummaryPanel('resultado', 'Resultado', 'Vendas e receita separadas entre Marketing e Operação.', [
                    ['resultado_receita_marketing', 'Receita Marketing', $previousMarketingRevenue, $marketingRevenue, true, ''],
                    ['resultado_receita_operacao', 'Receita Operação', $previousOperacaoRevenue, $operacaoRevenue, true, ''],
                ]),
            ],
            'competitor_signals' => $this->buildCompetitorSignals($empresa),
        ];
    }

    private function buildCompetitorsTab(?Empresa $empresa, Carbon $currentStart, Carbon $currentEnd): array
    {
        $query = $empresa
            ? ConcorrenteAd::query()->where('empresa_id', $empresa->id)
            : ConcorrenteAd::query();

        $ads = $query->orderByDesc('created_at')->get();
        $profiles = collect($this->concorrenteService->competitorProfiles($ads));

        $rows = $ads->map(function (ConcorrenteAd $ad) use ($profiles) {
            $profile = $profiles->firstWhere('nome', trim($ad->concorrente_nome ?: 'Concorrente')) ?? [];
            $score = (int) min(10, max(0, (($ad->ads_biblioteca_sinal ?? 0) > 0 ? 4 : 0) + (int) (($ad->feed_posts_visiveis ?? 0) > 0 ? 3 : 0)));
            $badge = $this->concorrenteService->buildScoreBadge($score);

            return [
                'id' => $ad->id,
                'concorrente_nome' => $ad->concorrente_nome,
                'activity_label' => $profile['activity_label'] ?? 'Sem Avaliação Feita',
                'activity_class' => $profile['activity_class'] ?? 'is-none',
                'score_digital_label' => $badge['label'],
                'score_digital_class' => $badge['class_name'],
                'plataforma' => $ad->plataforma ?: 'Meta Ads',
                'data_referencia' => $ad->data_referencia,
                'created_at' => $ad->created_at,
            ];
        })->values();

        return [
            'concorrentes_list' => $rows,
            'competitor_analysis_panels' => [],
            'company_digital' => null,
            'open_analysis' => '',
            'periodo_atual_resumo' => $currentStart->format('d/m/Y').' - '.$currentEnd->format('d/m/Y'),
        ];
    }

    private function configTabKey(ConfiguracaoUploadEmpresa $config): string
    {
        return $config->tipo_documento.'_'.$config->id;
    }

    private function enabledTableMetricKeys(string $tipoDocumento, ?array $rawConfig, ?string $variant = null): array
    {
        $config = is_array($rawConfig) ? $rawConfig : [];
        $enabled = [];
        foreach ($this->metricGroups($tipoDocumento, $variant) as $group) {
            foreach ($group['metrics'] as $metric) {
                $state = $config['metrics'][$metric['key']] ?? [];
                if (($state['table'] ?? true) === true) {
                    $enabled[] = $metric['key'];
                }
            }
        }

        return array_values(array_unique($enabled));
    }

    private function enabledChartMetricKeys(string $tipoDocumento, ?array $rawConfig, ?string $variant = null): array
    {
        $config = is_array($rawConfig) ? $rawConfig : [];
        $enabled = [];
        foreach ($this->metricGroups($tipoDocumento, $variant) as $group) {
            foreach ($group['metrics'] as $metric) {
                if (! $this->metricAllowsChart($tipoDocumento, $group['key'], $metric['key'], $variant)) {
                    continue;
                }
                $state = $config['metrics'][$metric['key']] ?? [];
                if (($state['chart'] ?? true) === true) {
                    $enabled[] = $metric['key'];
                }
            }
        }

        return array_values(array_unique($enabled));
    }

    private function metricAllowsChart(string $tipoDocumento, string $groupKey, string $metricKey, ?string $variant = null): bool
    {
        if ($tipoDocumento === self::REDES_SOCIAIS) {
            return $groupKey === 'visao_geral';
        }

        return true;
    }

    private function categoryFilterEnabledMap(string $tipoDocumento, ?array $rawConfig, ?string $variant = null): array
    {
        $config = is_array($rawConfig) ? $rawConfig : [];
        $filters = [];
        foreach ($this->metricGroups($tipoDocumento, $variant) as $group) {
            $filters[$group['key']] = (bool) ($config['filters'][$group['key']]['enabled'] ?? false);
        }

        return $filters;
    }

    private function metricGroups(string $tipoDocumento, ?string $variant = null): array
    {
        if ($tipoDocumento === self::TRAFEGO_PAGO) {
            return array_map(fn (array $group) => [
                'key' => $group['key'],
                'metrics' => array_map(fn (string $metricKey) => ['key' => $metricKey], $group['metrics']),
            ], self::TRAFFIC_BLOCK_DEFINITIONS);
        }

        if ($tipoDocumento === self::CRM_VENDAS) {
            return [
                ['key' => 'resultado', 'metrics' => array_map(fn ($key) => ['key' => $key], ['receita_total', 'vendas_concluidas', 'taxa_conversao', 'conversas', 'ticket_medio'])],
                ['key' => 'origem', 'metrics' => array_map(fn ($key) => ['key' => $key], ['receita_marketing_pago', 'receita_marketing_organico', 'receita_operacional', 'receita_sem_categoria'])],
                ['key' => 'temperatura', 'metrics' => [['key' => 'temperatura_lead']]],
            ];
        }

        if ($tipoDocumento === self::REDES_SOCIAIS) {
            return array_map(fn (array $group) => [
                'key' => $group['key'],
                'metrics' => array_map(fn (array $metric) => ['key' => $metric['key']], $group['metrics']),
            ], $this->socialBlockDefinitions($variant ?: 'instagram'));
        }

        return [];
    }

    private function readMappedRows(ConfiguracaoUploadEmpresa $config): array
    {
        if (! is_array($config->mapeamento_json) || $config->mapeamento_json === []) {
            return [];
        }

        $rows = [];
        foreach ($config->uploads_painel as $upload) {
            $path = Storage::path($upload->arquivo);
            if (! file_exists($path)) {
                continue;
            }

            $table = $this->campanhaService->readTable($path);
            foreach ($table as $sourceRow) {
                $row = [];
                foreach ($config->mapeamento_json as $fieldKey => $columnName) {
                    $row[$fieldKey] = $sourceRow[$columnName] ?? '';
                }
                $rows[] = $row;
            }
        }

        return $rows;
    }

    private function readSocialRows(ConfiguracaoUploadEmpresa $config): array
    {
        if (! is_array($config->mapeamento_json) || $config->mapeamento_json === []) {
            return [];
        }

        $digitalType = $this->getSocialDigitalType($config);
        $deduped = [];

        foreach ($config->uploads_painel as $upload) {
            $mapping = $config->mapeamento_json[$upload->tipo_upload] ?? $config->mapeamento_json['principal'] ?? [];
            if (! is_array($mapping) || $mapping === []) {
                continue;
            }

            $path = Storage::path($upload->arquivo);
            if (! file_exists($path)) {
                continue;
            }

            $table = $this->campanhaService->readTable($path)->values();
            foreach ($table as $index => $sourceRow) {
                $row = [];
                foreach ($mapping as $fieldKey => $columnName) {
                    $row[$fieldKey] = $sourceRow[$columnName] ?? '';
                }
                $resolvedPublishedAt = $this->parseSocialPublishedAt(
                    $row['data_publicacao'] ?? null,
                    $digitalType,
                    (string) $upload->nome_arquivo
                );
                if (! $resolvedPublishedAt) {
                    $fallbackDate = $sourceRow['Horário de publicação']
                        ?? $sourceRow['Horario de publicacao']
                        ?? $sourceRow['Data de Publicação']
                        ?? $sourceRow['Data de Publicacao']
                        ?? null;
                    $resolvedPublishedAt = $this->parseSocialPublishedAt(
                        $fallbackDate,
                        $digitalType,
                        (string) $upload->nome_arquivo
                    );
                }
                if ($resolvedPublishedAt) {
                    $row['data_publicacao'] = $resolvedPublishedAt->format('Y-m-d H:i:s');
                }
                $row['tipo_conteudo_normalizado'] = $this->normalizeSocialContentType(
                    (string) ($row['tipo_conteudo'] ?? ''),
                    (string) $upload->tipo_upload,
                    (string) $upload->nome_arquivo
                );

                $key = trim((string) ($row['id_publicacao'] ?? '')) ?: $upload->id.':'.$index.':'.$digitalType;
                $deduped[$key] = $row;
            }
        }

        $rows = array_values($deduped);
        usort($rows, fn (array $left, array $right) => strcmp((string) ($right['data_publicacao'] ?? ''), (string) ($left['data_publicacao'] ?? '')));

        return $rows;
    }

    private function filterRowsByPeriod(array $rows, Carbon $periodStart, Carbon $periodEnd, string $dateKey): array
    {
        return array_values(array_filter($rows, function (array $row) use ($periodStart, $periodEnd, $dateKey) {
            $date = $this->parseDate($row[$dateKey] ?? null);
            if (! $date) {
                return true;
            }

            return $date->betweenIncluded($periodStart, $periodEnd);
        }));
    }

    private function crmPeriodSummary(array $rows, array $closedStatus, ?ConfiguracaoUploadEmpresa $config): array
    {
        $conversations = count($rows);
        $closedRows = array_filter($rows, fn (array $row) => $this->crmIsClosedSale($row, $closedStatus));
        $revenue = collect($rows)->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0));
        $paidRows = array_filter($rows, fn (array $row) => $this->crmIsPaidRow($row, $config));
        $organicRows = array_filter($rows, fn (array $row) => $this->crmIsMarketingOrganicoRow($row, $config));
        $operationalRows = array_filter($rows, fn (array $row) => $this->crmIsOperacionalRow($row));
        $uncategorizedRows = array_filter($rows, fn (array $row) => ! $this->crmIsPaidRow($row, $config) && ! $this->crmIsMarketingOrganicoRow($row, $config) && ! $this->crmIsOperacionalRow($row));

        $statusCounts = [];
        $temperatureCounts = [];
        foreach ($rows as $row) {
            $status = trim((string) ($row['status_fechamento'] ?? '')) ?: 'Não informado';
            $statusCounts[$status] = ($statusCounts[$status] ?? 0) + 1;
            $temp = $this->normalizeLeadTemperatureLabel($row['tag_lead'] ?? '');
            $temperatureCounts[$temp] = ($temperatureCounts[$temp] ?? 0) + 1;
        }

        $temperatureCounts = $this->sortTemperatureCounts($temperatureCounts);

        return [
            'geral' => [
                'receita_total' => $revenue,
                'vendas_concluidas' => count($closedRows),
                'taxa_conversao' => $conversations > 0 ? (count($closedRows) / $conversations) * 100 : 0,
                'conversas' => $conversations,
                'ticket_medio' => count($closedRows) > 0 ? ($revenue / count($closedRows)) : 0,
            ],
            'origem' => [
                'trafego_pago_conversas' => count($paidRows),
                'organico_conversas' => $conversations - count($paidRows),
                'receita_marketing_pago' => collect($paidRows)->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0)),
                'receita_marketing_organico' => collect($organicRows)->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0)),
                'receita_operacional' => collect($operationalRows)->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0)),
                'receita_sem_categoria' => collect($uncategorizedRows)->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0)),
            ],
            'status_counts' => $statusCounts,
            'temperatura_counts' => $temperatureCounts,
            'temperatura' => collect($temperatureCounts)->map(fn (int $count, string $label) => count($rows) > 0 ? ($count / count($rows)) * 100 : 0)->all(),
        ];
    }

    private function buildCrmCategoryBlocks(array $selectedTableKeys, array $selectedChartKeys, array $currentSummary, array $previousSummary, array $filterEnabledMap): array
    {
        $blocks = [];

        $resultadoMetrics = [
            ['receita_total', 'Receita Total', true, ''],
            ['vendas_concluidas', 'Vendas Concluídas', false, ''],
            ['taxa_conversao', 'Taxa de Conversão', false, '%'],
            ['conversas', 'Conversas', false, ''],
            ['ticket_medio', 'Ticket Médio', true, ''],
        ];
        $resultadoRows = $this->crmComparisonRows($resultadoMetrics, $currentSummary['geral'], $previousSummary['geral'], $selectedTableKeys);
        if ($resultadoRows !== []) {
            $blocks[] = [
                'key' => 'resultado',
                'title' => 'Resultado',
                'description' => 'Comparativo principal entre os períodos do comercial.',
                'rows' => $resultadoRows,
                'chart' => null,
                'chart_type' => null,
                'filter_options' => ($filterEnabledMap['resultado'] ?? false) ? array_column($resultadoRows, 'label') : [],
            ];
        }

        $origemMetrics = [
            ['receita_marketing_pago', 'Marketing Pago', true, ''],
            ['receita_marketing_organico', 'Marketing Orgânico', true, ''],
            ['receita_operacional', 'Operacional', true, ''],
            ['receita_sem_categoria', 'Sem categoria', true, ''],
        ];
        $origemRows = $this->crmComparisonRows($origemMetrics, $currentSummary['origem'], $previousSummary['origem'], $selectedTableKeys);
        if ($origemRows !== []) {
            $blocks[] = [
                'key' => 'origem',
                'title' => 'Origem',
                'description' => 'Composição da receita por origem: marketing pago, orgânico, operacional e sem categoria.',
                'rows' => $origemRows,
                'chart' => null,
                'chart_type' => null,
                'filter_options' => ($filterEnabledMap['origem'] ?? false) ? array_column($origemRows, 'label') : [],
            ];
        }

        if (in_array('temperatura_lead', $selectedTableKeys, true) || in_array('temperatura_lead', $selectedChartKeys, true)) {
            $temperatureRows = $this->crmStatusComparisonRows(
                $currentSummary['temperatura_counts'],
                $previousSummary['temperatura_counts'],
                in_array('temperatura_lead', $selectedTableKeys, true),
                fn (string $label) => $this->crmTemperatureColor($label),
            );
            $blocks[] = [
                'key' => 'temperatura',
                'title' => 'Temperatura Leads',
                'description' => 'Distribuição atual em pizza e comparação por temperatura na tabela.',
                'rows' => $temperatureRows,
                'chart' => in_array('temperatura_lead', $selectedChartKeys, true) ? $this->crmDistributionPieChart($currentSummary['temperatura'], 'crm_temperatura', fn (string $label) => $this->crmTemperatureColor($label)) : null,
                'chart_type' => 'pie',
                'filter_options' => ($filterEnabledMap['temperatura'] ?? false) ? array_column($temperatureRows, 'label') : [],
            ];
        }

        return $blocks;
    }

    private function crmComparisonRows(array $metricDefs, array $currentValues, array $previousValues, array $selectedTableKeys): array
    {
        $rows = [];
        foreach ($metricDefs as [$key, $label, $currency, $suffix]) {
            if (! in_array($key, $selectedTableKeys, true)) {
                continue;
            }

            $current = $currentValues[$key] ?? 0;
            $previous = $previousValues[$key] ?? 0;
            $absolute = $current - $previous;
            $percent = $previous != 0 ? ($absolute / $previous) * 100 : null;

            $rows[] = [
                'label' => $label,
                'period_value' => $this->formatMetric($previous, $currency, $suffix).' / '.$this->formatMetric($current, $currency, $suffix),
                'previous_value' => $this->formatMetric($previous, $currency, $suffix),
                'current_value' => $this->formatMetric($current, $currency, $suffix),
                'variation_value' => $this->formatVariation($absolute, $percent, $key),
                'variation_class' => $this->resolvePositiveVariationClass($absolute, $key, $percent, ['receita_total', 'vendas_concluidas', 'taxa_conversao', 'conversas', 'ticket_medio', 'receita_marketing_pago', 'receita_marketing_organico', 'receita_operacional', 'receita_sem_categoria']),
            ];
        }

        return $rows;
    }

    private function crmStatusComparisonRows(array $currentCounts, array $previousCounts, bool $includeTable, callable $colorFn): array
    {
        if (! $includeTable) {
            return [];
        }

        $labels = array_values(array_unique([...array_keys($currentCounts), ...array_keys($previousCounts)]));
        sort($labels);
        $rows = [];
        foreach ($labels as $label) {
            $current = (int) ($currentCounts[$label] ?? 0);
            $previous = (int) ($previousCounts[$label] ?? 0);
            $absolute = $current - $previous;
            $percent = $previous !== 0 ? ($absolute / $previous) * 100 : null;
            $rows[] = [
                'label' => $label,
                'label_color' => $colorFn($label),
                'period_value' => br_number($previous, 0).' / '.br_number($current, 0),
                'previous_value' => br_number($previous, 0),
                'current_value' => br_number($current, 0),
                'variation_value' => $this->formatVariation($absolute, $percent, 'conversas'),
                'variation_class' => $this->resolvePositiveVariationClass($absolute, 'conversas', $percent, ['conversas']),
            ];
        }

        return $rows;
    }

    private function crmDistributionPieChart(array $distribution, string $key, callable $colorFn): ?array
    {
        if ($distribution === []) {
            return null;
        }

        $labels = array_keys($distribution);

        return [
            'key' => $key,
            'labels' => $labels,
            'series' => array_map(fn (string $label) => round((float) $distribution[$label], 2), $labels),
            'colors' => array_map($colorFn, $labels),
        ];
    }

    private function buildOrigemStackedAreaChart(array $allRows, ?ConfiguracaoUploadEmpresa $config): ?array
    {
        if ($allRows === []) {
            return null;
        }

        $groups = collect($allRows)->groupBy(function (array $row) {
            $date = $this->parseDate($row['data_contato'] ?? null);
            return $date ? $date->format('Y-m') : null;
        })->filter(fn (Collection $items, $key) => filled($key) && $items->isNotEmpty());

        $keys = $groups->keys()->sort()->take(-12)->values();
        if ($keys->isEmpty()) {
            return null;
        }

        $categories = $keys->map(fn (string $month) => Carbon::createFromFormat('Y-m', $month)->translatedFormat('M/y'))->values()->all();
        $series = [
            ['name' => 'Receita Total', 'type' => 'line', 'data' => []],
            ['name' => 'Marketing Pago', 'type' => 'area', 'data' => []],
            ['name' => 'Marketing Orgânico', 'type' => 'area', 'data' => []],
            ['name' => 'Operacional', 'type' => 'area', 'data' => []],
            ['name' => 'Sem categoria', 'type' => 'area', 'data' => []],
        ];

        foreach ($keys as $month) {
            $monthRows = $groups->get($month, collect());
            $summary = $this->crmPeriodSummary($monthRows->values()->all(), ['ganho', 'fechado', 'fechada', 'venda', 'vendido'], $config);
            $series[0]['data'][] = round((float) ($summary['geral']['receita_total'] ?? 0), 2);
            $series[1]['data'][] = round((float) ($summary['origem']['receita_marketing_pago'] ?? 0), 2);
            $series[2]['data'][] = round((float) ($summary['origem']['receita_marketing_organico'] ?? 0), 2);
            $series[3]['data'][] = round((float) ($summary['origem']['receita_operacional'] ?? 0), 2);
            $series[4]['data'][] = round((float) ($summary['origem']['receita_sem_categoria'] ?? 0), 2);
        }

        return [
            'key' => 'crm_origem_stacked',
            'categories' => $categories,
            'series' => $series,
            'colors' => ['#0f172a', '#175cd3', '#2d6a4f', '#c67a1a', '#94a3b8'],
            'chart_type' => 'mixed_area',
        ];
    }

    private function socialBlockDefinitions(string $digitalType): array
    {
        return match ($digitalType) {
            'website' => [
                ['key' => 'visao_geral', 'title' => 'Visão Geral', 'description' => 'Leitura consolidada do tráfego do website no período.', 'metrics' => [['key' => 'usuarios', 'label' => 'Usuários'], ['key' => 'sessoes', 'label' => 'Sessões'], ['key' => 'visualizacoes_pagina', 'label' => 'Visualizações de Página']], 'chart_metrics' => ['usuarios', 'sessoes', 'visualizacoes_pagina']],
                ['key' => 'aquisicao', 'title' => 'Aquisição', 'description' => 'Indicadores de aquisição e qualidade de sessão.', 'metrics' => [['key' => 'novos_usuarios', 'label' => 'Novos Usuários'], ['key' => 'sessoes_engajadas', 'label' => 'Sessões Engajadas'], ['key' => 'taxa_engajamento', 'label' => 'Taxa de Engajamento']], 'chart_metrics' => ['novos_usuarios', 'sessoes_engajadas', 'taxa_engajamento']],
                ['key' => 'conversao', 'title' => 'Conversão', 'description' => 'Indicadores de resultado do website.', 'metrics' => [['key' => 'conversoes', 'label' => 'Conversões']], 'chart_metrics' => ['conversoes']],
            ],
            'tiktok' => [
                ['key' => 'visao_geral', 'title' => 'Visão Geral', 'description' => 'Desempenho consolidado do conteúdo publicado no TikTok.', 'metrics' => [['key' => 'quantidade_publicacoes', 'label' => 'Quantidade de Conteúdos'], ['key' => 'visualizacoes', 'label' => 'Visualizações'], ['key' => 'alcance', 'label' => 'Alcance']], 'chart_metrics' => ['quantidade_publicacoes', 'visualizacoes', 'alcance']],
                ['key' => 'engajamento', 'title' => 'Engajamento', 'description' => 'Interações do conteúdo com a audiência.', 'metrics' => [['key' => 'curtidas', 'label' => 'Curtidas'], ['key' => 'compartilhamentos', 'label' => 'Compartilhamentos'], ['key' => 'comentarios', 'label' => 'Comentários'], ['key' => 'salvamentos', 'label' => 'Salvamentos']], 'chart_metrics' => ['curtidas', 'compartilhamentos', 'comentarios']],
                ['key' => 'audiencia', 'title' => 'Audiência', 'description' => 'Sinais de interesse pela conta e crescimento.', 'metrics' => [['key' => 'visitas_perfil', 'label' => 'Visitas ao Perfil'], ['key' => 'seguimentos', 'label' => 'Seguimentos']], 'chart_metrics' => ['visitas_perfil', 'seguimentos']],
            ],
            'x' => [
                ['key' => 'visao_geral', 'title' => 'Visão Geral', 'description' => 'Desempenho consolidado do conteúdo publicado no X.', 'metrics' => [['key' => 'quantidade_publicacoes', 'label' => 'Quantidade de Posts'], ['key' => 'visualizacoes', 'label' => 'Impressões'], ['key' => 'alcance', 'label' => 'Alcance']], 'chart_metrics' => ['quantidade_publicacoes', 'visualizacoes', 'alcance']],
                ['key' => 'interacao', 'title' => 'Interação', 'description' => 'Respostas e compartilhamentos do conteúdo.', 'metrics' => [['key' => 'curtidas', 'label' => 'Curtidas'], ['key' => 'compartilhamentos', 'label' => 'Reposts / Compartilhamentos'], ['key' => 'comentarios', 'label' => 'Respostas']], 'chart_metrics' => ['curtidas', 'compartilhamentos', 'comentarios']],
                ['key' => 'trafego', 'title' => 'Tráfego', 'description' => 'Sinais de tráfego gerado e interesse no perfil.', 'metrics' => [['key' => 'cliques_link', 'label' => 'Cliques no Link'], ['key' => 'visitas_perfil', 'label' => 'Visitas ao Perfil'], ['key' => 'seguimentos', 'label' => 'Seguimentos']], 'chart_metrics' => ['cliques_link', 'visitas_perfil', 'seguimentos']],
            ],
            default => [
                ['key' => 'visao_geral', 'title' => 'Visão Geral', 'description' => 'Bloco principal consolidado do desempenho social.', 'metrics' => [['key' => 'quantidade_publicacoes', 'label' => 'Quantidade de Publicações'], ['key' => 'visualizacoes', 'label' => 'Visualizações'], ['key' => 'alcance', 'label' => 'Alcance'], ['key' => 'curtidas', 'label' => 'Curtidas'], ['key' => 'compartilhamentos', 'label' => 'Compartilhamentos']], 'chart_metrics' => ['quantidade_publicacoes', 'visualizacoes', 'alcance']],
                ['key' => 'posts', 'title' => 'Posts', 'description' => 'Desempenho consolidado apenas dos conteúdos do tipo post.', 'metrics' => [['key' => 'quantidade_posts', 'label' => 'Quantidade de Posts'], ['key' => 'visualizacoes_posts', 'label' => 'Visualizações dos Posts'], ['key' => 'alcance_posts', 'label' => 'Alcance dos Posts'], ['key' => 'curtidas_posts', 'label' => 'Curtidas dos Posts'], ['key' => 'compartilhamentos_posts', 'label' => 'Compartilhamentos dos Posts']], 'chart_metrics' => ['quantidade_posts', 'visualizacoes_posts', 'alcance_posts']],
                ['key' => 'stories', 'title' => 'Stories', 'description' => 'Desempenho consolidado apenas dos conteúdos do tipo story.', 'metrics' => [['key' => 'quantidade_stories', 'label' => 'Quantidade de Stories'], ['key' => 'visualizacoes_stories', 'label' => 'Visualizações dos Stories'], ['key' => 'alcance_stories', 'label' => 'Alcance dos Stories'], ['key' => 'curtidas_stories', 'label' => 'Curtidas dos Stories'], ['key' => 'compartilhamentos_stories', 'label' => 'Compartilhamentos dos Stories']], 'chart_metrics' => ['quantidade_stories', 'visualizacoes_stories', 'alcance_stories']],
                ['key' => 'engajamento', 'title' => 'Engajamento', 'description' => 'Indicadores complementares de interação.', 'metrics' => [['key' => 'curtidas', 'label' => 'Curtidas'], ['key' => 'compartilhamentos', 'label' => 'Compartilhamentos'], ['key' => 'comentarios', 'label' => 'Comentários'], ['key' => 'salvamentos', 'label' => 'Salvamentos'], ['key' => 'respostas', 'label' => 'Respostas'], ['key' => 'cliques_link', 'label' => 'Cliques no Link'], ['key' => 'visitas_perfil', 'label' => 'Visitas ao Perfil']], 'chart_metrics' => ['curtidas', 'compartilhamentos', 'comentarios']],
            ],
        };
    }

    private function buildSocialCategoryBlocks(string $digitalType, array $selectedTableKeys, array $currentSummary, array $previousSummary, array $filterEnabledMap): array
    {
        $blocks = [];
        foreach ($this->socialBlockDefinitions($digitalType) as $definition) {
            $rows = [];
            foreach ($definition['metrics'] as $metricDef) {
                if (! in_array($metricDef['key'], $selectedTableKeys, true)) {
                    continue;
                }

                $current = $currentSummary[$metricDef['key']] ?? 0;
                $previous = $previousSummary[$metricDef['key']] ?? 0;
                $absolute = $current - $previous;
                $percent = $previous != 0 ? ($absolute / $previous) * 100 : null;

                $rows[] = [
                    'label' => $metricDef['label'],
                    'current_value' => $this->formatMetric($current, false, Str::contains($metricDef['label'], 'Taxa') ? '%' : ''),
                    'previous_value' => $this->formatMetric($previous, false, Str::contains($metricDef['label'], 'Taxa') ? '%' : ''),
                    'variation_value' => $this->formatVariation($absolute, $percent, $metricDef['key']),
                    'variation_class' => $this->resolvePositiveVariationClass($absolute, $metricDef['key'], $percent, array_keys($currentSummary)),
                ];
            }

            if ($rows !== []) {
                $blocks[] = [
                    'key' => $definition['key'],
                    'title' => $definition['title'],
                    'description' => $definition['description'],
                    'rows' => $rows,
                    'chart' => null,
                    'chart_type' => null,
                    'filter_options' => ($filterEnabledMap[$definition['key']] ?? false) ? array_column($rows, 'label') : [],
                ];
            }
        }

        return $blocks;
    }

    private function socialPeriodSummary(array $rows, string $digitalType): array
    {
        $sum = fn (string $key) => collect($rows)->sum(fn (array $row) => $this->toFloat($row[$key] ?? 0));

        if ($digitalType === 'website') {
            $usuarios = $sum('usuarios');
            $sessoes = $sum('sessoes');
            $sessoesEngajadas = $sum('sessoes_engajadas');
            $visualizacoes = $sum('visualizacoes_pagina');

            return [
                'usuarios' => $usuarios,
                'novos_usuarios' => $sum('novos_usuarios'),
                'sessoes' => $sessoes,
                'sessoes_engajadas' => $sessoesEngajadas,
                'visualizacoes_pagina' => $visualizacoes,
                'taxa_engajamento' => $sessoes > 0 ? ($sessoesEngajadas / $sessoes) * 100 : 0,
                'conversoes' => $sum('conversoes'),
                'visualizacoes' => $visualizacoes,
                'alcance' => $usuarios,
            ];
        }

        $posts = array_filter($rows, fn (array $row) => ($row['tipo_conteudo_normalizado'] ?? 'post') === 'post');
        $stories = array_filter($rows, fn (array $row) => ($row['tipo_conteudo_normalizado'] ?? 'post') === 'story');

        return [
            'quantidade_publicacoes' => count($rows),
            'visualizacoes' => $sum('visualizacoes'),
            'alcance' => $sum('alcance'),
            'curtidas' => $sum('curtidas'),
            'compartilhamentos' => $sum('compartilhamentos'),
            'quantidade_posts' => count($posts),
            'visualizacoes_posts' => collect($posts)->sum(fn (array $row) => $this->toFloat($row['visualizacoes'] ?? 0)),
            'alcance_posts' => collect($posts)->sum(fn (array $row) => $this->toFloat($row['alcance'] ?? 0)),
            'curtidas_posts' => collect($posts)->sum(fn (array $row) => $this->toFloat($row['curtidas'] ?? 0)),
            'compartilhamentos_posts' => collect($posts)->sum(fn (array $row) => $this->toFloat($row['compartilhamentos'] ?? 0)),
            'quantidade_stories' => count($stories),
            'visualizacoes_stories' => collect($stories)->sum(fn (array $row) => $this->toFloat($row['visualizacoes'] ?? 0)),
            'alcance_stories' => collect($stories)->sum(fn (array $row) => $this->toFloat($row['alcance'] ?? 0)),
            'curtidas_stories' => collect($stories)->sum(fn (array $row) => $this->toFloat($row['curtidas'] ?? 0)),
            'compartilhamentos_stories' => collect($stories)->sum(fn (array $row) => $this->toFloat($row['compartilhamentos'] ?? 0)),
            'comentarios' => $sum('comentarios'),
            'salvamentos' => $sum('salvamentos'),
            'respostas' => $sum('respostas'),
            'cliques_link' => $sum('cliques_link'),
            'visitas_perfil' => $sum('visitas_perfil'),
            'seguimentos' => $sum('seguimentos'),
        ];
    }

    private function aggregateSocialSummaries(array $summaries): array
    {
        return [
            'visualizacoes' => collect($summaries)->sum('visualizacoes'),
            'alcance' => collect($summaries)->sum('alcance'),
        ];
    }

    private function getSocialDigitalType(ConfiguracaoUploadEmpresa $config): string
    {
        return (string) ($config->configuracao_analise_json['digital_type'] ?? 'instagram');
    }

    private function socialTabDescription(string $digitalType): string
    {
        return match ($digitalType) {
            'website' => 'Comparativo de tráfego e conversão do website com base nos uploads reais do Google Analytics.',
            'tiktok' => 'Comparativo do desempenho orgânico do TikTok entre período atual e anterior.',
            'x' => 'Comparativo do desempenho orgânico do X / Twitter entre período atual e anterior.',
            default => 'Comparativo do desempenho orgânico entre período atual e anterior, baseado apenas em uploads reais.',
        };
    }

    private function buildTrafficMetricDefinitions(string $resultLabel): array
    {
        return [
            'investimento' => ['label' => 'Investimento Total', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['investimento'], 'currency' => true, 'suffix' => ''],
            'cpm' => ['label' => 'CPM', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['cpm'], 'currency' => true, 'suffix' => ''],
            'cpc' => ['label' => 'CPC', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['cpc'], 'currency' => true, 'suffix' => ''],
            'cpl' => ['label' => 'CPL', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['cpl'], 'currency' => true, 'suffix' => ''],
            'impressoes' => ['label' => 'Impressões', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['impressoes'], 'currency' => false, 'suffix' => ''],
            'alcance' => ['label' => 'Alcance', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['alcance'], 'currency' => false, 'suffix' => ''],
            'ctr' => ['label' => 'CTR', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['ctr'], 'currency' => false, 'suffix' => '%'],
            'taxa_conversao' => ['label' => 'Taxa de Conversão', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['taxa_conversao'], 'currency' => false, 'suffix' => '%'],
            'frequencia' => ['label' => 'Frequência', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['frequencia'], 'currency' => false, 'suffix' => ''],
            'score_relevancia' => ['label' => 'Score de Relevância', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['score_relevancia'], 'currency' => false, 'suffix' => '/10'],
            'cpm_relativo' => ['label' => 'CPM relativo', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['cpm_relativo'], 'currency' => false, 'suffix' => 'x'],
            'resultado_principal' => ['label' => $resultLabel, 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['resultado_principal'], 'currency' => false, 'suffix' => ''],
            'custo_por_resultado' => ['label' => 'Custo por Resultado', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['custo_por_resultado'], 'currency' => true, 'suffix' => ''],
            'taxa_resposta' => ['label' => 'Taxa de Resposta', 'tooltip' => self::TRAFFIC_METRIC_TOOLTIPS['taxa_resposta'], 'currency' => false, 'suffix' => '%'],
        ];
    }

    private function buildTrafficMetricValues(array $summary, array $previousSummary): array
    {
        $investimento = (float) ($summary['investimento'] ?? 0);
        $impressoes = (float) ($summary['impressoes'] ?? 0);
        $alcance = (float) ($summary['alcance'] ?? 0);
        $cliques = (float) ($summary['cliques'] ?? 0);
        $resultados = (float) ($summary['resultados'] ?? 0);
        $cpm = (float) ($summary['cpm'] ?? 0);
        $previousCpm = (float) ($previousSummary['cpm'] ?? 0);
        $taxaConversao = $cliques > 0 ? ($resultados / $cliques) * 100 : 0;
        $frequencia = $alcance > 0 ? $impressoes / $alcance : 0;

        return [
            'investimento' => $investimento,
            'cpm' => $cpm,
            'cpc' => (float) ($summary['cpc'] ?? 0),
            'cpl' => (float) ($summary['cpl'] ?? 0),
            'impressoes' => $impressoes,
            'alcance' => $alcance,
            'ctr' => (float) ($summary['ctr'] ?? 0),
            'taxa_conversao' => $taxaConversao,
            'frequencia' => $frequencia,
            'score_relevancia' => $this->calculateRelevanceScore((float) ($summary['ctr'] ?? 0), (float) ($summary['cpc'] ?? 0), $cpm, $frequencia, $taxaConversao),
            'cpm_relativo' => $previousCpm > 0 ? ($cpm / $previousCpm) : 1,
            'resultado_principal' => $resultados,
            'custo_por_resultado' => (float) ($summary['cpl'] ?? 0),
            'taxa_resposta' => $taxaConversao,
        ];
    }

    private function buildTrafficBlocks(array $metricValues, array $previousMetrics, array $definitions, array $selectedKeys, array $filterEnabledMap): array
    {
        $blocks = [];
        foreach (self::TRAFFIC_BLOCK_DEFINITIONS as $block) {
            $rows = [];
            foreach ($block['metrics'] as $metricKey) {
                if (! in_array($metricKey, $selectedKeys, true)) {
                    continue;
                }

                $current = $metricValues[$metricKey] ?? 0;
                $previous = $previousMetrics[$metricKey] ?? 0;
                $absolute = $current - $previous;
                $percent = $previous != 0 ? ($absolute / $previous) * 100 : null;
                $definition = $definitions[$metricKey];
                $rows[] = [
                    'label' => $definition['label'],
                    'tooltip' => $definition['tooltip'],
                    'current_value' => $this->formatMetric($current, $definition['currency'], $definition['suffix']),
                    'previous_value' => $this->formatMetric($previous, $definition['currency'], $definition['suffix']),
                    'variation_value' => $this->formatVariation($absolute, $percent, $metricKey),
                    'variation_class' => $this->resolveTrafficVariationClass($metricKey, $absolute, $percent),
                ];
            }

            if ($rows !== []) {
                $blocks[] = [
                    'key' => $block['key'],
                    'title' => $block['title'],
                    'description' => $block['description'],
                    'highlighted' => $block['highlighted'],
                    'rows' => $rows,
                    'filter_options' => ($filterEnabledMap[$block['key']] ?? false) ? array_column($rows, 'label') : [],
                ];
            }
        }

        return $blocks;
    }

    private function buildTrafficLineChart(int $empresaId, array $chartKeys, array $definitions): ?array
    {
        if ($chartKeys === []) {
            return null;
        }

        $monthly = CampanhaMetric::query()
            ->selectRaw("DATE_FORMAT(data, '%Y-%m') as month_key")
            ->selectRaw('SUM(investimento) as investimento')
            ->selectRaw('SUM(impressoes) as impressoes')
            ->selectRaw('SUM(alcance) as alcance')
            ->selectRaw('SUM(cliques) as cliques')
            ->selectRaw('SUM(resultados) as resultados')
            ->whereHas('upload', fn ($query) => $query->where('empresa_id', $empresaId))
            ->groupBy('month_key')
            ->orderBy('month_key')
            ->get();

        if ($monthly->isEmpty()) {
            return null;
        }

        $categories = $monthly->map(fn ($row) => Carbon::createFromFormat('Y-m', $row->month_key)->translatedFormat('M/y'))->all();
        $series = [];

        foreach ($chartKeys as $metricKey) {
            if (! isset($definitions[$metricKey])) {
                continue;
            }

            $series[] = [
                'name' => $definitions[$metricKey]['label'],
                'data' => $monthly->map(function ($row) use ($metricKey) {
                    $summary = [
                        'investimento' => (float) $row->investimento,
                        'impressoes' => (float) $row->impressoes,
                        'alcance' => (float) $row->alcance,
                        'cliques' => (float) $row->cliques,
                        'resultados' => (float) $row->resultados,
                        'ctr' => (float) ($row->impressoes > 0 ? ($row->cliques / $row->impressoes) * 100 : 0),
                        'cpc' => (float) ($row->cliques > 0 ? ($row->investimento / $row->cliques) : 0),
                        'cpm' => (float) ($row->impressoes > 0 ? ($row->investimento / $row->impressoes) * 1000 : 0),
                        'cpl' => (float) ($row->resultados > 0 ? ($row->investimento / $row->resultados) : 0),
                    ];
                    return round($this->buildTrafficMetricValues($summary, [])[$metricKey] ?? 0, 2);
                })->all(),
            ];
        }

        return ['categories' => $categories, 'series' => $series];
    }

    private function buildSocialMonthlyLineChart(array $allRows, string $digitalType, array $metricDefs, array $chartKeys): ?array
    {
        if ($allRows === [] || $chartKeys === []) {
            return null;
        }

        $groups = collect($allRows)->groupBy(function (array $row) {
            $date = $this->parseDate($row['data_publicacao'] ?? null);
            return $date ? $date->format('Y-m') : null;
        })->filter(fn (Collection $items, $key) => filled($key) && $items->isNotEmpty());

        $keys = $groups->keys()->sort()->take(-12)->values();
        if ($keys->isEmpty()) {
            return null;
        }

        $metricMap = collect($metricDefs)->keyBy('key');
        $categories = $keys->map(fn (string $month) => Carbon::createFromFormat('Y-m', $month)->translatedFormat('M/y'))->values()->all();
        $series = [];
        foreach ($chartKeys as $key) {
            $label = $metricMap[$key]['label'] ?? $key;
            $series[] = [
                'name' => $label,
                'data' => $keys->map(function (string $month) use ($groups, $digitalType, $key) {
                    $monthRows = $groups->get($month, collect());
                    $summary = $this->socialPeriodSummary($monthRows->values()->all(), $digitalType);
                    return round((float) ($summary[$key] ?? 0), 2);
                })->all(),
            ];
        }

        return ['categories' => $categories, 'series' => $series];
    }

    private function buildLeadsMonthlyLineChart(ConfiguracaoUploadEmpresa $config): ?array
    {
        $grouped = collect($config->eventos_painel)
            ->groupBy(fn (EventoPainel $item) => $item->data_evento->format('Y-m'))
            ->map(fn (Collection $items) => $items->sum('leads_media'));

        if ($grouped->isEmpty()) {
            return null;
        }

        $keys = $grouped->keys()->sort()->take(-12)->values();
        return [
            'categories' => $keys->map(fn (string $month) => Carbon::createFromFormat('Y-m', $month)->translatedFormat('M/y'))->all(),
            'series' => [
                [
                    'name' => 'Pessoas alcançadas',
                    'data' => $keys->map(fn (string $month) => (int) $grouped->get($month, 0))->all(),
                ],
            ],
        ];
    }

    private function buildExecutiveChart(?Empresa $empresa, ?ConfiguracaoUploadEmpresa $crmConfig, Collection $socialConfigs = new Collection, Collection $leadsConfigs = new Collection): ?array
    {
        if (! $empresa) {
            return null;
        }

        // Load all social rows per config once, then group by month
        $socialMonthlyAlcance = [];
        $socialRowsByConfig = [];
        foreach ($socialConfigs as $config) {
            $type = $this->getSocialDigitalType($config);
            $allRows = $this->readSocialRows($config);
            $socialRowsByConfig[] = ['type' => $type, 'rows' => $allRows];
            $grouped = collect($allRows)->groupBy(function (array $row) {
                $date = $this->parseDate($row['data_publicacao'] ?? null);
                return $date ? $date->format('Y-m') : null;
            })->filter(fn (Collection $items, $key) => filled($key));
            foreach ($grouped as $month => $rows) {
                $summary = $this->socialPeriodSummary($rows->values()->all(), $type);
                $socialMonthlyAlcance[$month] = ($socialMonthlyAlcance[$month] ?? 0) + (float) ($summary['alcance'] ?? 0);
            }
        }

        $crmRows = $crmConfig ? $this->readMappedRows($crmConfig) : [];
        $crmGroups = collect($crmRows)->groupBy(function (array $row) {
            $date = $this->parseDate($row['data_contato'] ?? null);
            return $date ? $date->format('Y-m') : null;
        })->filter(fn (Collection $items, $key) => filled($key) && $items->isNotEmpty());

        $keys = collect([...array_keys($socialMonthlyAlcance), ...$crmGroups->keys()->all()])->unique()->sort()->take(-12)->values();
        if ($keys->isEmpty()) {
            return null;
        }

        return [
            'categories' => $keys->map(fn (string $month) => Carbon::createFromFormat('Y-m', $month)->translatedFormat('M/y'))->all(),
            'series' => [
                ['name' => 'Alcance (Presença Digital)', 'data' => $keys->map(fn (string $month) => round((float) ($socialMonthlyAlcance[$month] ?? 0), 2))->all()],
                ['name' => 'Receita Marketing', 'data' => $keys->map(function (string $month) use ($crmGroups, $crmConfig, $socialConfigs, $socialRowsByConfig, $leadsConfigs) {
                    $monthStart = Carbon::createFromFormat('Y-m', $month)->startOfMonth();
                    $monthEnd = Carbon::createFromFormat('Y-m', $month)->endOfMonth();

                    // Per-month social summaries per config (mirrors how the card computes the share)
                    $monthSocialSummaries = [];
                    foreach ($socialRowsByConfig as $item) {
                        $monthRows = collect($item['rows'])->filter(function (array $row) use ($monthStart, $monthEnd) {
                            $date = $this->parseDate($row['data_publicacao'] ?? null);
                            return $date && $date->betweenIncluded($monthStart, $monthEnd);
                        })->values()->all();
                        $monthSocialSummaries[] = $this->socialPeriodSummary($monthRows, $item['type']);
                    }

                    // Per-month leads entries
                    $monthLeadsEntries = [];
                    foreach ($leadsConfigs as $config) {
                        foreach ($config->eventos_painel as $entry) {
                            if ($entry->data_evento->betweenIncluded($monthStart, $monthEnd)) {
                                $monthLeadsEntries[] = $entry;
                            }
                        }
                    }

                    $monthShare = $this->combinedMarketingShare($socialConfigs, $monthSocialSummaries, $leadsConfigs, $monthLeadsEntries);

                    $monthRows = $crmGroups->get($month, collect())->values()->all();
                    $marketingRevenue = collect(array_filter($monthRows, fn (array $row) => $this->isMarketingSale($row, $crmConfig)))
                        ->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0));
                    $operacaoRevenue = collect(array_filter($monthRows, fn (array $row) => $this->isOperacaoOrSemCategoriaSale($row, $crmConfig)))
                        ->sum(fn (array $row) => $this->toFloat($row['valor_venda'] ?? 0));

                    return round($marketingRevenue + $operacaoRevenue * $monthShare, 2);
                })->all()],
                ['name' => 'Conversas (Tráfego Pago)', 'data' => $keys->map(function (string $month) use ($crmGroups, $crmConfig) {
                    $monthRows = $crmGroups->get($month, collect());
                    $summary = $this->crmPeriodSummary($monthRows->values()->all(), ['ganho', 'fechado', 'fechada', 'venda', 'vendido'], $crmConfig);
                    return round((float) ($summary['origem']['trafego_pago_conversas'] ?? 0), 2);
                })->all()],
            ],
        ];
    }

    private function buildSummaryPanel(string $key, string $title, string $description, array $metrics): array
    {
        $rows = [];
        foreach ($metrics as [$metricKey, $label, $previous, $current, $currency, $suffix]) {
            $absolute = $current - $previous;
            $percent = $previous != 0 ? ($absolute / $previous) * 100 : null;
            $rows[] = [
                'label' => $label,
                'current_value' => $this->formatMetric($current, $currency, $suffix),
                'previous_value' => $this->formatMetric($previous, $currency, $suffix),
                'variation_value' => $this->formatVariation($absolute, $percent, $metricKey),
                'variation_class' => $this->resolvePositiveVariationClass($absolute, $metricKey, $percent, [$metricKey]),
            ];
        }

        return compact('key', 'title', 'description', 'rows');
    }

    private function filterLeadsEntries(ConfiguracaoUploadEmpresa $config, Carbon $start, Carbon $end): array
    {
        return $config->eventos_painel
            ->filter(fn (EventoPainel $item) => $item->data_evento->betweenIncluded($start, $end))
            ->values()
            ->all();
    }

    private function buildCompetitorSignals(?Empresa $empresa): array
    {
        if (! $empresa) {
            return [];
        }

        return collect($this->concorrenteService->competitorProfiles(
            ConcorrenteAd::query()->where('empresa_id', $empresa->id)->get()
        ))->take(5)->map(fn (array $item) => [
            'nome' => $item['nome'],
            'atividade' => $item['activity_label'],
            'ads_count' => $item['real_ads_count'],
            'cadencia' => $item['feed_cadencia'] ?: 'Sem leitura de cadência',
        ])->values()->all();
    }

    private function combinedMarketingShare(Collection $socialConfigs, array $socialSummaries, Collection $leadsConfigs, array $leadEntries): float
    {
        $share = 0.0;

        foreach ($socialConfigs as $index => $config) {
            $rate = (float) ($config->configuracao_analise_json['social_receita_percentual_por_1k_alcance'] ?? 0);
            $reach = (float) ($socialSummaries[$index]['alcance'] ?? 0);
            $share += min(100, max(0, ($reach / 1000) * $rate)) / 100;
        }

        foreach ($leadsConfigs as $config) {
            $rate = (float) ($config->configuracao_analise_json['eventos_receita_percentual_por_1k_alcance'] ?? 0);
            $reach = (float) collect($leadEntries)->sum('leads_media');
            $share += min(100, max(0, ($reach / 1000) * $rate)) / 100;
        }

        return min(0.4, max(0, $share));
    }

    private function crmIsPaidRow(array $row, ?ConfiguracaoUploadEmpresa $config): bool
    {
        $url = Str::lower(trim((string) ($row['ads_parametros_url'] ?? '')));
        $contains = Str::lower(trim((string) ($config?->configuracao_analise_json['crm_origem_paga_contem'] ?? '')));
        return Str::startsWith($url, 'https://www.') || ($contains !== '' && Str::contains($url, $contains));
    }

    private function crmIsMarketingOrganicoRow(array $row, ?ConfiguracaoUploadEmpresa $config): bool
    {
        if ($this->crmIsPaidRow($row, $config)) {
            return false;
        }

        $origem = $this->normalizeStatusLabel($row['origem_lead'] ?? '');
        return Str::contains($origem, ['marketing', 'google']);
    }

    private function crmIsOperacionalRow(array $row): bool
    {
        $origem = $this->normalizeStatusLabel($row['origem_lead'] ?? '');
        return Str::contains($origem, ['cliente base', 'indicacao', 'indicação']);
    }

    private function crmIsClosedSale(array $row, array $closedStatus): bool
    {
        $status = $this->normalizeStatusLabel($row['status_fechamento'] ?? '');
        $revenue = $this->toFloat($row['valor_venda'] ?? 0);
        return $revenue > 0 || in_array($status, $closedStatus, true) || Str::contains($status, ['venda concluida', 'venda concluída', 'fechado', 'ganho', 'vendido']);
    }

    private function isMarketingSale(array $row, ?ConfiguracaoUploadEmpresa $config): bool
    {
        $origem = $this->normalizeStatusLabel($row['origem_lead'] ?? '');
        return Str::contains($origem, ['marketing', 'google']) || $this->crmIsPaidRow($row, $config) || $this->isPaidTrafficSale($row);
    }

    private function isOperacaoOrSemCategoriaSale(array $row, ?ConfiguracaoUploadEmpresa $config): bool
    {
        return $this->crmIsOperacionalRow($row) || ! $this->isMarketingSale($row, $config);
    }

    private function isPaidTrafficSale(array $row): bool
    {
        $haystack = Str::lower(implode(' ', [
            (string) ($row['origem_lead'] ?? ''),
            (string) ($row['canal'] ?? ''),
            (string) ($row['tag_lead'] ?? ''),
        ]));

        foreach (self::PAID_TRAFFIC_HINTS as $hint) {
            if (Str::contains($haystack, $hint)) {
                return true;
            }
        }

        return false;
    }

    private function normalizeSocialContentType(string $value, string $uploadType, string $fileName): string
    {
        $normalized = $this->normalizeStatusLabel($value);
        $uploadHint = $this->normalizeStatusLabel($uploadType);
        $fileHint = $this->normalizeStatusLabel($fileName);

        if (Str::contains($normalized, ['story', 'stories', 'storie'])) {
            return 'story';
        }
        if (Str::contains($normalized, ['post', 'feed', 'photo', 'foto', 'carousel', 'carrossel'])) {
            return 'post';
        }
        if (Str::contains($uploadHint, ['stories', 'story']) || Str::contains($fileHint, ['stories', 'story'])) {
            return 'story';
        }

        return 'post';
    }

    private function normalizeStatusLabel(mixed $value): string
    {
        $text = Str::lower(trim((string) $value));
        $text = Str::ascii($text);
        return preg_replace('/^\s*\d+\s*-\s*/', '', $text) ?: '';
    }

    private function normalizeLeadTemperatureLabel(mixed $value): string
    {
        $text = $this->normalizeStatusLabel($value);
        if ($text === '') {
            return 'Não informado';
        }
        if (Str::contains($text, 'cliente')) {
            return 'Cliente';
        }
        if (Str::contains($text, 'muito quente')) {
            return 'Muito Quente';
        }
        if (Str::contains($text, 'quente')) {
            return 'Quente';
        }
        if (Str::contains($text, 'frio')) {
            return 'Frio';
        }
        return 'Não informado';
    }

    private function sortTemperatureCounts(array $counts): array
    {
        $ordered = [];
        foreach (self::LEAD_TEMPERATURE_DISPLAY_ORDER as $label) {
            if (isset($counts[$label])) {
                $ordered[$label] = $counts[$label];
            }
        }
        foreach ($counts as $label => $value) {
            if (! isset($ordered[$label])) {
                $ordered[$label] = $value;
            }
        }
        return $ordered;
    }

    private function crmTemperatureColor(string $label): string
    {
        $normalized = $this->normalizeStatusLabel($label);
        foreach (self::LEAD_TEMPERATURE_COLOR_RULES as [$term, $color]) {
            if (Str::contains($normalized, $term)) {
                return $color;
            }
        }
        return '#175cd3';
    }

    private function resolveResultLabel(ConfiguracaoUploadEmpresa $config): string
    {
        $mappedColumn = $config->mapeamento_json['tipo_resultado'] ?? null;
        if (! $mappedColumn) {
            return 'Resultado Principal';
        }

        $values = collect($config->preview_json ?? [])
            ->map(fn (array $row) => trim((string) ($row[$mappedColumn] ?? '')))
            ->filter()
            ->values();

        if ($values->isEmpty()) {
            return 'Resultado Principal';
        }

        return $values->countBy()->sortDesc()->keys()->first() ?: 'Resultado Principal';
    }

    private function calculateRelevanceScore(float $ctr, float $cpc, float $cpm, float $frequencia, float $taxaConversao): float
    {
        $score = 0;
        $score += $ctr >= 1.50 ? 3 : ($ctr >= 0.90 ? 2 : 1);
        $score += $cpc <= 1.50 ? 2 : ($cpc <= 3.00 ? 1 : 0);
        $score += $cpm <= 30 ? 2 : ($cpm <= 60 ? 1 : 0);
        $score += $frequencia <= 2.50 ? 1.5 : ($frequencia <= 4.00 ? 0.5 : 0);
        $score += $taxaConversao >= 8 ? 1.5 : ($taxaConversao >= 3 ? 1 : 0.5);
        return min(10, $score);
    }

    private function formatMetric(float|int $value, bool $currency = false, string $suffix = ''): string
    {
        if ($currency) {
            return br_currency($value);
        }
        if ($suffix === '%') {
            return br_number($value, 2).'%';
        }
        if ($suffix === 'x') {
            return br_number($value, 2).'x';
        }
        if ($suffix === '/10') {
            return br_number($value, 1).'/10';
        }
        return br_number($value, $suffix === '' ? null : 2);
    }

    private function formatVariation(float|int $absolute, ?float $percent, string $key): string
    {
        $absoluteText = match ($key) {
            'investimento', 'cpm', 'cpc', 'cpl', 'custo_por_resultado', 'receita_total', 'ticket_medio', 'receita_marketing_pago', 'receita_marketing_organico', 'receita_operacional', 'receita_sem_categoria', 'resultado_receita_marketing', 'resultado_receita_operacao' => br_currency($absolute),
            'ctr', 'taxa_conversao', 'taxa_resposta', 'atendimento_taxa_conversao', 'taxa_engajamento' => br_number($absolute, 2).'pp',
            'cpm_relativo' => br_number($absolute, 2).'x',
            'score_relevancia' => br_number($absolute, 1),
            default => br_number($absolute, 0),
        };

        return $percent === null ? $absoluteText : $absoluteText.' ('.br_number($percent, 2).'%)';
    }

    private function resolveTrafficVariationClass(string $key, float|int $absolute, ?float $percent): string
    {
        $positiveWhenHigher = ['impressoes', 'alcance', 'ctr', 'taxa_conversao', 'resultado_principal', 'taxa_resposta', 'score_relevancia'];
        $positiveWhenLower = ['investimento', 'cpm', 'cpc', 'cpl', 'frequencia', 'cpm_relativo', 'custo_por_resultado'];

        if ($absolute == 0) {
            return 'text-muted';
        }

        $favorable = in_array($key, $positiveWhenHigher, true) ? $absolute > 0 : (in_array($key, $positiveWhenLower, true) ? $absolute < 0 : null);
        if ($favorable === null) {
            return 'text-muted';
        }

        return $this->variationTone($favorable, $percent);
    }

    private function resolvePositiveVariationClass(float|int $absolute, string $key, ?float $percent, array $positiveKeys): string
    {
        if ($absolute == 0) {
            return 'text-muted';
        }

        if (! in_array($key, $positiveKeys, true)) {
            return 'text-muted';
        }

        return $this->variationTone($absolute > 0, $percent);
    }

    private function variationTone(bool $favorable, ?float $percent): string
    {
        if ($percent === null) {
            return $favorable ? 'text-info' : 'text-warning';
        }

        $intensity = abs($percent);
        if ($favorable) {
            return $intensity <= 10 ? 'text-info' : 'text-success';
        }

        return $intensity <= 10 ? 'text-warning' : 'text-danger';
    }

    private function eventoImpactoLabel(string $impacto): string
    {
        return match ($impacto) {
            'alto' => 'Alto',
            'medio' => 'Médio',
            'baixo' => 'Baixo',
            default => Str::headline($impacto),
        };
    }

    private function parseDate(mixed $value): ?Carbon
    {
        if (! $value) {
            return null;
        }

        if ($value instanceof Carbon) {
            return $value->copy();
        }

        $text = trim((string) $value);
        if ($text === '') {
            return null;
        }

        try {
            if (preg_match('/^\d{4}-\d{2}-\d{2}/', $text)) {
                return Carbon::parse($text)->startOfDay();
            }
            if (str_contains($text, '/')) {
                return $this->parseSlashDate($text, false)?->startOfDay();
            }
            return Carbon::parse($text)->startOfDay();
        } catch (\Throwable) {
            return null;
        }
    }

    private function parseSocialPublishedAt(mixed $value, string $digitalType, string $fileName = ''): ?Carbon
    {
        if (! $value) {
            return null;
        }

        $text = trim((string) $value);
        if ($text === '' || strcasecmp($text, 'total') === 0) {
            return null;
        }

        if (preg_match('/^\d{4}-\d{2}-\d{2}/', $text)) {
            try {
                return Carbon::parse($text);
            } catch (\Throwable) {
                return null;
            }
        }

        $preferUs = in_array($digitalType, ['instagram', 'facebook', 'tiktok'], true);
        if ($preferUs && str_contains($text, '/')) {
            return $this->parseSlashDate($text, true);
        }

        return $this->parseDate($text);
    }

    private function parseSlashDate(string $text, bool $preferUs): ?Carbon
    {
        if (! preg_match('/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?$/', $text, $matches)) {
            return null;
        }

        $first = (int) $matches[1];
        $second = (int) $matches[2];
        $year = (int) $matches[3];
        $hour = isset($matches[4]) ? (int) $matches[4] : 0;
        $minute = isset($matches[5]) ? (int) $matches[5] : 0;
        $secondValue = isset($matches[6]) ? (int) $matches[6] : 0;

        $candidates = [];
        if ($preferUs) {
            $candidates[] = [$second, $first];
            $candidates[] = [$first, $second];
        } else {
            $candidates[] = [$first, $second];
            $candidates[] = [$second, $first];
        }

        foreach ($candidates as [$day, $month]) {
            if (! checkdate($month, $day, $year)) {
                continue;
            }

            try {
                return Carbon::create($year, $month, $day, $hour, $minute, $secondValue);
            } catch (\Throwable) {
            }
        }

        return null;
    }

    private function toFloat(mixed $value): float
    {
        if (is_numeric($value)) {
            return (float) $value;
        }

        $text = trim((string) $value);
        if ($text === '') {
            return 0.0;
        }

        $text = str_replace(['R$', '%', ' '], '', $text);
        if (str_contains($text, ',') && str_contains($text, '.')) {
            $text = strrpos($text, ',') > strrpos($text, '.') ? str_replace('.', '', str_replace(',', '.', $text)) : str_replace(',', '', $text);
        } elseif (str_contains($text, ',')) {
            $text = str_replace('.', '', str_replace(',', '.', $text));
        }

        return is_numeric($text) ? (float) $text : 0.0;
    }
}
