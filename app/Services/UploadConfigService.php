<?php

namespace App\Services;

use App\Models\ConfiguracaoUploadEmpresa;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Arr;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class UploadConfigService
{
    public const TYPE_OPTIONS = [
        'trafego_pago' => 'Ads Digital',
        'crm_vendas' => 'Vendas',
        'redes_sociais' => 'Presença Digital',
        'leads_eventos' => 'Presença Física',
    ];

    public const DIGITAL_TYPE_OPTIONS = [
        'instagram' => 'Instagram',
        'facebook' => 'Facebook',
        'tiktok' => 'TikTok',
        'website' => 'Website',
        'x' => 'X / Twitter',
        'outro' => 'Outro',
    ];

    public const ADS_TYPE_OPTIONS = [
        'meta_ads' => 'Meta Ads',
        'google_ads' => 'Google Ads',
        'tiktok_ads' => 'TikTok Ads',
        'outro' => 'Outro',
    ];

    public const SOCIAL_MAPPING_TYPES = [
        'instagram' => [
            ['key' => 'posts', 'label' => 'Posts'],
            ['key' => 'stories', 'label' => 'Stories'],
        ],
        'default' => [
            ['key' => 'principal', 'label' => 'Arquivo principal'],
        ],
    ];

    public function __construct(
        private readonly CampanhaService $campanhaService,
    ) {
    }

    public function typeOptions(): array
    {
        return self::TYPE_OPTIONS;
    }

    public function digitalTypeOptions(): array
    {
        return self::DIGITAL_TYPE_OPTIONS;
    }

    public function adsTypeOptions(): array
    {
        return self::ADS_TYPE_OPTIONS;
    }

    public function mappingTypesForSocial(string $digitalType): array
    {
        return self::SOCIAL_MAPPING_TYPES[$digitalType] ?? self::SOCIAL_MAPPING_TYPES['default'];
    }

    public function inspectUploadedFile(UploadedFile|string $file, ?string $originalName = null): array
    {
        $rows = $this->campanhaService->readTable($file instanceof UploadedFile ? $file->getRealPath() : $file);
        $rows = $rows instanceof Collection ? $rows : collect($rows);
        $first = $rows->first() ?: [];
        $columns = array_keys(is_array($first) ? $first : []);

        return [
            'columns' => $columns,
            'rows' => $rows->take(5)->values()->all(),
            'file_name' => $originalName ?: ($file instanceof UploadedFile ? $file->getClientOriginalName() : basename((string) $file)),
        ];
    }

    public function storeExampleFile(UploadedFile $file): string
    {
        return $file->store('empresas/upload-configs');
    }

    public function deleteStoredFile(?string $path): void
    {
        if ($path && Storage::exists($path)) {
            Storage::delete($path);
        }
    }

    public function fieldSchema(string $tipoDocumento, ?string $variant = null): array
    {
        return match ($tipoDocumento) {
            'trafego_pago' => [
                ['key' => 'nome_campanha', 'label' => 'Nome da campanha', 'required' => true],
                ['key' => 'anuncios', 'label' => 'Anúncios', 'required' => false],
                ['key' => 'alcance', 'label' => 'Alcance', 'required' => false],
                ['key' => 'impressoes', 'label' => 'Impressões', 'required' => false],
                ['key' => 'tipo_resultado', 'label' => 'Tipo de resultado', 'required' => false],
                ['key' => 'resultados', 'label' => 'Resultados', 'required' => false],
                ['key' => 'valor_usado_brl', 'label' => 'Valor usado (BRL)', 'required' => true],
                ['key' => 'custo_por_resultado', 'label' => 'Custo por resultado', 'required' => false],
                ['key' => 'cliques_link', 'label' => 'Cliques no link', 'required' => false],
                ['key' => 'cpc_link', 'label' => 'CPC (custo por clique no link)', 'required' => false],
                ['key' => 'cpm', 'label' => 'CPM (custo por 1.000 impressões)', 'required' => false],
                ['key' => 'ctr_todos', 'label' => 'CTR (todos)', 'required' => false],
                ['key' => 'visualizacoes', 'label' => 'Visualizações', 'required' => false],
            ],
            'crm_vendas' => [
                ['key' => 'id', 'label' => 'ID', 'required' => true],
                ['key' => 'data_contato', 'label' => 'Data do Contato', 'required' => true],
                ['key' => 'nome_lead', 'label' => 'Nome do Lead', 'required' => true],
                ['key' => 'informacao_contato', 'label' => 'Informação do Contato', 'required' => false],
                ['key' => 'canal', 'label' => 'Canal', 'required' => false],
                ['key' => 'valor_venda', 'label' => 'Valor da Venda', 'required' => false],
                ['key' => 'vendedor', 'label' => 'Vendedor', 'required' => false],
                ['key' => 'tag_lead', 'label' => 'Tag Lead', 'required' => false],
                ['key' => 'status_fechamento', 'label' => 'Status Fechamento', 'required' => false],
                ['key' => 'origem_lead', 'label' => 'Origem do Lead', 'required' => false],
                ['key' => 'ads_parametros_url', 'label' => 'Ads (Parâmetros de URL)', 'required' => false],
            ],
            'redes_sociais' => $this->socialFieldSchema($variant ?: 'instagram'),
            default => [],
        };
    }

    public function metricGroups(string $tipoDocumento, ?string $variant = null): array
    {
        return match ($tipoDocumento) {
            'trafego_pago' => [
                ['key' => 'resultados', 'label' => 'Resultados', 'description' => 'Bloco principal de conversão, preparado para múltiplas plataformas e objetivos.', 'metrics' => [
                    ['key' => 'resultado_principal', 'label' => 'Resultado Principal'],
                    ['key' => 'custo_por_resultado', 'label' => 'Custo por Resultado'],
                    ['key' => 'taxa_resposta', 'label' => 'Taxa de Resposta'],
                ]],
                ['key' => 'custo_investimento', 'label' => 'Custo e Investimento', 'description' => 'Controle financeiro do período e eficiência básica do investimento.', 'metrics' => [
                    ['key' => 'investimento', 'label' => 'Investimento Total'],
                    ['key' => 'cpm', 'label' => 'CPM'],
                    ['key' => 'cpc', 'label' => 'CPC'],
                    ['key' => 'cpl', 'label' => 'CPL'],
                ]],
                ['key' => 'performance_anuncios', 'label' => 'Performance dos Anúncios', 'description' => 'Entrega, alcance e capacidade de gerar ação ao longo do funil.', 'metrics' => [
                    ['key' => 'impressoes', 'label' => 'Impressões'],
                    ['key' => 'alcance', 'label' => 'Alcance'],
                    ['key' => 'ctr', 'label' => 'CTR'],
                    ['key' => 'taxa_conversao', 'label' => 'Taxa de Conversão'],
                    ['key' => 'frequencia', 'label' => 'Frequência'],
                ]],
                ['key' => 'qualidade_relevancia', 'label' => 'Qualidade e Relevância', 'description' => 'Leitura sintética da saúde do criativo e da pressão de mídia.', 'metrics' => [
                    ['key' => 'score_relevancia', 'label' => 'Score de Relevância'],
                    ['key' => 'cpm_relativo', 'label' => 'CPM relativo'],
                ]],
            ],
            'crm_vendas' => [
                ['key' => 'resultado', 'label' => 'Resultado', 'description' => 'Comparativo principal entre os períodos do comercial.', 'metrics' => [
                    ['key' => 'receita_total', 'label' => 'Receita Total'],
                    ['key' => 'vendas_concluidas', 'label' => 'Vendas Concluídas'],
                    ['key' => 'taxa_conversao', 'label' => 'Taxa de Conversão'],
                    ['key' => 'conversas', 'label' => 'Conversas'],
                    ['key' => 'ticket_medio', 'label' => 'Ticket Médio'],
                ]],
                ['key' => 'origem', 'label' => 'Origem', 'description' => 'Composição da receita por origem.', 'metrics' => [
                    ['key' => 'receita_marketing_pago', 'label' => 'Marketing Pago'],
                    ['key' => 'receita_marketing_organico', 'label' => 'Marketing Orgânico'],
                    ['key' => 'receita_operacional', 'label' => 'Operacional'],
                    ['key' => 'receita_sem_categoria', 'label' => 'Sem categoria'],
                ]],
                ['key' => 'temperatura', 'label' => 'Temperatura Leads', 'description' => 'Distribuição por temperatura do lead.', 'metrics' => [
                    ['key' => 'temperatura_lead', 'label' => 'Temperatura do Lead'],
                ]],
            ],
            'redes_sociais' => $this->socialMetricGroups($variant ?: 'instagram'),
            default => [],
        };
    }

    public function normalizeMetricConfig(string $tipoDocumento, ?array $rawConfig, ?string $variant = null): array
    {
        $config = is_array($rawConfig) ? $rawConfig : [];
        $normalized = [
            'metrics' => [],
            'filters' => [],
        ];

        foreach ($this->metricGroups($tipoDocumento, $variant) as $group) {
            $normalized['filters'][$group['key']] = [
                'enabled' => (bool) Arr::get($config, "filters.{$group['key']}.enabled", false),
            ];
            foreach ($group['metrics'] as $metric) {
                $state = Arr::get($config, "metrics.{$metric['key']}", []);
                $chartAllowed = $this->metricAllowsChart($tipoDocumento, $group['key'], $metric['key'], $variant);
                $normalized['metrics'][$metric['key']] = [
                    'table' => array_key_exists('table', $state) ? (bool) $state['table'] : true,
                    'chart' => $chartAllowed
                        ? (array_key_exists('chart', $state) ? (bool) $state['chart'] : true)
                        : false,
                ];
            }
        }

        return $normalized;
    }

    public function metricAllowsChart(string $tipoDocumento, string $groupKey, string $metricKey, ?string $variant = null): bool
    {
        if ($tipoDocumento === 'redes_sociais') {
            return $groupKey === 'visao_geral';
        }

        return true;
    }

    private function socialFieldSchema(string $digitalType): array
    {
        return match ($digitalType) {
            'website' => [
                ['key' => 'id_publicacao', 'label' => 'ID da Sessão / Registro', 'required' => false],
                ['key' => 'data_publicacao', 'label' => 'Data de Referência', 'required' => true],
                ['key' => 'usuarios', 'label' => 'Usuários', 'required' => false],
                ['key' => 'novos_usuarios', 'label' => 'Novos Usuários', 'required' => false],
                ['key' => 'sessoes', 'label' => 'Sessões', 'required' => false],
                ['key' => 'sessoes_engajadas', 'label' => 'Sessões Engajadas', 'required' => false],
                ['key' => 'visualizacoes_pagina', 'label' => 'Visualizações de Página', 'required' => false],
                ['key' => 'conversoes', 'label' => 'Conversões', 'required' => false],
            ],
            default => [
                ['key' => 'id_publicacao', 'label' => 'ID da Publicação', 'required' => false],
                ['key' => 'data_publicacao', 'label' => 'Data de Publicação', 'required' => true],
                ['key' => 'tipo_conteudo', 'label' => 'Tipo de Conteúdo', 'required' => false],
                ['key' => 'descricao', 'label' => 'Descrição', 'required' => false],
                ['key' => 'link_permanente', 'label' => 'Link Permanente', 'required' => false],
                ['key' => 'visualizacoes', 'label' => 'Visualizações', 'required' => false],
                ['key' => 'alcance', 'label' => 'Alcance', 'required' => false],
                ['key' => 'curtidas', 'label' => 'Curtidas', 'required' => false],
                ['key' => 'compartilhamentos', 'label' => 'Compartilhamentos', 'required' => false],
                ['key' => 'comentarios', 'label' => 'Comentários', 'required' => false],
                ['key' => 'salvamentos', 'label' => 'Salvamentos', 'required' => false],
                ['key' => 'respostas', 'label' => 'Respostas', 'required' => false],
                ['key' => 'cliques_link', 'label' => 'Cliques no Link', 'required' => false],
                ['key' => 'visitas_perfil', 'label' => 'Visitas ao Perfil', 'required' => false],
                ['key' => 'seguimentos', 'label' => 'Seguimentos', 'required' => false],
            ],
        };
    }

    private function socialMetricGroups(string $digitalType): array
    {
        return match ($digitalType) {
            'website' => [
                ['key' => 'visao_geral', 'label' => 'Visão Geral', 'description' => 'Leitura consolidada do tráfego do website no período.', 'metrics' => [
                    ['key' => 'usuarios', 'label' => 'Usuários'],
                    ['key' => 'sessoes', 'label' => 'Sessões'],
                    ['key' => 'visualizacoes_pagina', 'label' => 'Visualizações de Página'],
                ]],
                ['key' => 'aquisicao', 'label' => 'Aquisição', 'description' => 'Indicadores de aquisição e qualidade de sessão.', 'metrics' => [
                    ['key' => 'novos_usuarios', 'label' => 'Novos Usuários'],
                    ['key' => 'sessoes_engajadas', 'label' => 'Sessões Engajadas'],
                    ['key' => 'taxa_engajamento', 'label' => 'Taxa de Engajamento'],
                ]],
                ['key' => 'conversao', 'label' => 'Conversão', 'description' => 'Indicadores de resultado do website.', 'metrics' => [
                    ['key' => 'conversoes', 'label' => 'Conversões'],
                ]],
            ],
            'tiktok' => [
                ['key' => 'visao_geral', 'label' => 'Visão Geral', 'description' => 'Desempenho consolidado do conteúdo publicado no TikTok.', 'metrics' => [
                    ['key' => 'quantidade_publicacoes', 'label' => 'Quantidade de Conteúdos'],
                    ['key' => 'visualizacoes', 'label' => 'Visualizações'],
                    ['key' => 'alcance', 'label' => 'Alcance'],
                ]],
                ['key' => 'engajamento', 'label' => 'Engajamento', 'description' => 'Interações do conteúdo com a audiência.', 'metrics' => [
                    ['key' => 'curtidas', 'label' => 'Curtidas'],
                    ['key' => 'compartilhamentos', 'label' => 'Compartilhamentos'],
                    ['key' => 'comentarios', 'label' => 'Comentários'],
                    ['key' => 'salvamentos', 'label' => 'Salvamentos'],
                ]],
                ['key' => 'audiencia', 'label' => 'Audiência', 'description' => 'Sinais de interesse pela conta e crescimento.', 'metrics' => [
                    ['key' => 'visitas_perfil', 'label' => 'Visitas ao Perfil'],
                    ['key' => 'seguimentos', 'label' => 'Seguimentos'],
                ]],
            ],
            'x' => [
                ['key' => 'visao_geral', 'label' => 'Visão Geral', 'description' => 'Desempenho consolidado do conteúdo publicado no X.', 'metrics' => [
                    ['key' => 'quantidade_publicacoes', 'label' => 'Quantidade de Posts'],
                    ['key' => 'visualizacoes', 'label' => 'Impressões'],
                    ['key' => 'alcance', 'label' => 'Alcance'],
                ]],
                ['key' => 'interacao', 'label' => 'Interação', 'description' => 'Respostas e compartilhamentos do conteúdo.', 'metrics' => [
                    ['key' => 'curtidas', 'label' => 'Curtidas'],
                    ['key' => 'compartilhamentos', 'label' => 'Reposts / Compartilhamentos'],
                    ['key' => 'comentarios', 'label' => 'Respostas'],
                ]],
                ['key' => 'trafego', 'label' => 'Tráfego', 'description' => 'Sinais de tráfego gerado e interesse no perfil.', 'metrics' => [
                    ['key' => 'cliques_link', 'label' => 'Cliques no Link'],
                    ['key' => 'visitas_perfil', 'label' => 'Visitas ao Perfil'],
                    ['key' => 'seguimentos', 'label' => 'Seguimentos'],
                ]],
            ],
            default => [
                ['key' => 'visao_geral', 'label' => 'Visão Geral', 'description' => 'Bloco principal consolidado do desempenho social.', 'metrics' => [
                    ['key' => 'quantidade_publicacoes', 'label' => 'Quantidade de Publicações'],
                    ['key' => 'visualizacoes', 'label' => 'Visualizações'],
                    ['key' => 'alcance', 'label' => 'Alcance'],
                    ['key' => 'curtidas', 'label' => 'Curtidas'],
                    ['key' => 'compartilhamentos', 'label' => 'Compartilhamentos'],
                ]],
                ['key' => 'posts', 'label' => 'Posts', 'description' => 'Desempenho consolidado apenas dos conteúdos do tipo post.', 'metrics' => [
                    ['key' => 'quantidade_posts', 'label' => 'Quantidade de Posts'],
                    ['key' => 'visualizacoes_posts', 'label' => 'Visualizações dos Posts'],
                    ['key' => 'alcance_posts', 'label' => 'Alcance dos Posts'],
                    ['key' => 'curtidas_posts', 'label' => 'Curtidas dos Posts'],
                    ['key' => 'compartilhamentos_posts', 'label' => 'Compartilhamentos dos Posts'],
                ]],
                ['key' => 'stories', 'label' => 'Stories', 'description' => 'Desempenho consolidado apenas dos conteúdos do tipo story.', 'metrics' => [
                    ['key' => 'quantidade_stories', 'label' => 'Quantidade de Stories'],
                    ['key' => 'visualizacoes_stories', 'label' => 'Visualizações dos Stories'],
                    ['key' => 'alcance_stories', 'label' => 'Alcance dos Stories'],
                    ['key' => 'curtidas_stories', 'label' => 'Curtidas dos Stories'],
                    ['key' => 'compartilhamentos_stories', 'label' => 'Compartilhamentos dos Stories'],
                ]],
                ['key' => 'engajamento', 'label' => 'Engajamento', 'description' => 'Indicadores complementares de interação.', 'metrics' => [
                    ['key' => 'curtidas', 'label' => 'Curtidas'],
                    ['key' => 'compartilhamentos', 'label' => 'Compartilhamentos'],
                    ['key' => 'comentarios', 'label' => 'Comentários'],
                    ['key' => 'salvamentos', 'label' => 'Salvamentos'],
                    ['key' => 'respostas', 'label' => 'Respostas'],
                    ['key' => 'cliques_link', 'label' => 'Cliques no Link'],
                    ['key' => 'visitas_perfil', 'label' => 'Visitas ao Perfil'],
                ]],
            ],
        };
    }
}
