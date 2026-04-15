<?php

namespace App\Http\Controllers;

use App\Models\Empresa;
use App\Models\ConfiguracaoUploadEmpresa;
use App\Models\User;
use App\Services\EmpresaService;
use App\Services\UploadConfigService;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;

class EmpresaController extends Controller
{
    public function index()
    {
        $empresa = Empresa::query()->orderBy('id')->first();
        if ($empresa) {
            return redirect()->route('empresas.detail', $empresa->id);
        }

        return redirect()->route('empresas.create');
    }

    public function create(EmpresaService $service)
    {
        if (Empresa::query()->exists()) {
            $empresa = Empresa::query()->orderBy('id')->first();
            return redirect()->route('empresas.update', $empresa->id);
        }

        return view('empresas.create', [
            'segmentos' => $this->segmentos(),
            'redes_sociais_texto' => $service->socialLinksToTextarea([]),
        ]);
    }

    public function store(Request $request, EmpresaService $service)
    {
        if (Empresa::query()->exists()) {
            $empresa = Empresa::query()->orderBy('id')->first();
            return redirect()->route('empresas.update', $empresa->id);
        }

        $data = $request->validate([
            'nome' => 'required|string|max:255',
            'cnpj' => 'nullable|string|max:50',
            'segmento' => 'nullable|string|max:100',
            'redes_sociais_texto' => 'nullable|string',
            'instagram_profile_url' => 'nullable|string|max:255',
            'ads_biblioteca_query' => 'nullable|string|max:255',
            'seguidores' => 'nullable|integer|min:0',
            'posts_total_publicos' => 'nullable|integer|min:0',
            'feed_posts_visiveis' => 'nullable|integer|min:0',
            'feed_cadencia' => 'nullable|string|max:100',
            'observacoes' => 'nullable|string',
            'ativo' => 'nullable|boolean',
        ]);
        $data = $this->prepareEmpresaPayload($data, $request, $service);
        $empresa = Empresa::create($data);
        return redirect()->route('empresas.detail', $empresa->id)->with('status', 'Empresa criada com sucesso.');
    }

    public function show(Empresa $empresa, EmpresaService $service)
    {
        $empresa->load('configuracoes_upload');
        $empresa_observacoes = $service->stripEmpresaLegacyDigitalNotes($empresa->observacoes);
        return view('empresas.detail', [
            'empresa' => $empresa,
            'empresa_observacoes' => $empresa_observacoes,
            'configuracoes_upload' => $empresa->configuracoes_upload,
        ]);
    }

    public function panels(Empresa $empresa, EmpresaService $service, UploadConfigService $uploadConfigService)
    {
        $empresa->load('configuracoes_upload');
        $empresa_observacoes = $service->stripEmpresaLegacyDigitalNotes($empresa->observacoes);

        return view('empresas.panels', [
            'empresa' => $empresa,
            'empresa_observacoes' => $empresa_observacoes,
            'configuracoes_upload' => $empresa->configuracoes_upload,
            'type_options' => $uploadConfigService->typeOptions(),
        ]);
    }

    public function edit(Empresa $empresa, EmpresaService $service)
    {
        $usuarios = User::query()->orderBy('id')->get();
        return view('empresas.edit', [
            'empresa' => $empresa,
            'usuarios' => $usuarios,
            'segmentos' => $this->segmentos(),
            'redes_sociais_texto' => $service->socialLinksToTextarea($empresa->redes_sociais_json),
        ]);
    }

    public function update(Request $request, Empresa $empresa, EmpresaService $service)
    {
        $data = $request->validate([
            'nome' => 'required|string|max:255',
            'cnpj' => 'nullable|string|max:50',
            'segmento' => 'nullable|string|max:100',
            'redes_sociais_texto' => 'nullable|string',
            'instagram_profile_url' => 'nullable|string|max:255',
            'ads_biblioteca_query' => 'nullable|string|max:255',
            'seguidores' => 'nullable|integer|min:0',
            'posts_total_publicos' => 'nullable|integer|min:0',
            'feed_posts_visiveis' => 'nullable|integer|min:0',
            'feed_cadencia' => 'nullable|string|max:100',
            'observacoes' => 'nullable|string',
            'ativo' => 'nullable|boolean',
        ]);
        $data = $this->prepareEmpresaPayload($data, $request, $service);
        $empresa->update($data);
        return redirect()->route('empresas.detail', $empresa->id)->with('status', 'Empresa atualizada com sucesso.');
    }

    public function destroy(Empresa $empresa)
    {
        $empresa->delete();
        return redirect()->route('empresas.list')->with('status', 'Empresa removida com sucesso.');
    }

    public function userStore(Request $request, Empresa $empresa)
    {
        $data = $request->validate([
            'name' => 'required|string|max:255',
            'email' => 'required|email|unique:users,email',
            'password' => 'required|string|min:6|confirmed',
        ]);

        User::create([
            'name' => $data['name'],
            'email' => $data['email'],
            'password' => Hash::make($data['password']),
        ]);

        return redirect()->route('empresas.update', $empresa->id)->with('status', 'Usuário criado com sucesso.');
    }

    public function uploadConfigCreate(Request $request, Empresa $empresa)
    {
        $data = $request->validate([
            'nome' => 'required|string|max:255',
        ]);
        $config = new ConfiguracaoUploadEmpresa($data);
        $config->empresa_id = $empresa->id;
        $config->save();
        return redirect()
            ->route('empresas.upload_config_update', [$empresa->id, $config->id])
            ->with('status', 'Painel criado com sucesso. Continue a configuração.');
    }

    public function uploadConfigEdit(Empresa $empresa, ConfiguracaoUploadEmpresa $config, UploadConfigService $service)
    {
        return view('empresas.upload_config', $this->buildUploadConfigViewData($empresa, $config, $service));
    }

    public function uploadConfigUpdate(Request $request, Empresa $empresa, ConfiguracaoUploadEmpresa $config, UploadConfigService $service)
    {
        $action = (string) $request->input('action', 'salvar');

        if ($action === 'limpar_arquivo') {
            $service->deleteStoredFile($config->arquivo_exemplo);
            $config->update([
                'arquivo_exemplo' => '',
                'nome_arquivo_exemplo' => '',
                'colunas_detectadas_json' => null,
                'preview_json' => null,
            ]);

            return redirect()->route('empresas.upload_config_update', [$empresa->id, $config->id])->with('status', 'Planilha de exemplo removida.');
        }

        $validated = $request->validate([
            'nome' => 'required|string|max:255',
            'tipo_documento' => 'required|string|max:50',
            'digital_type' => 'nullable|string|max:50',
            'ads_type' => 'nullable|string|max:50',
            'social_example_kind' => 'nullable|string|max:50',
            'crm_origem_paga_contem' => 'nullable|string|max:255',
            'social_receita_percentual_por_1k_alcance' => 'nullable|numeric|min:0',
            'eventos_receita_percentual_por_1k_alcance' => 'nullable|numeric|min:0',
            'arquivo_exemplo' => 'nullable|file|mimes:csv,txt,xlsx,xls',
        ]);

        $tipoDocumento = (string) $validated['tipo_documento'];
        $digitalType = (string) ($validated['digital_type'] ?? ($config->configuracao_analise_json['digital_type'] ?? 'instagram'));
        $socialKind = (string) ($validated['social_example_kind'] ?? 'posts');
        $uploadedFile = $request->file('arquivo_exemplo');

        if ($action === 'mapear') {
            if (! $uploadedFile) {
                return back()->withErrors(['arquivo_exemplo' => 'Envie um arquivo para mapear as colunas.'])->withInput();
            }

            $preview = $service->inspectUploadedFile($uploadedFile, $uploadedFile->getClientOriginalName());
            $analysis = $config->configuracao_analise_json ?? [];
            $analysis['digital_type'] = $digitalType;
            $analysis['ads_type'] = (string) ($validated['ads_type'] ?? ($analysis['ads_type'] ?? 'meta_ads'));
            $analysis['social_example_kind'] = $socialKind;

            if ($tipoDocumento === 'redes_sociais') {
                $socialPreviews = is_array($analysis['social_previews'] ?? null) ? $analysis['social_previews'] : [];
                $socialPreviews[$socialKind] = $preview;
                $analysis['social_previews'] = $socialPreviews;
                $config->update([
                    'nome' => $validated['nome'],
                    'tipo_documento' => $tipoDocumento,
                    'configuracao_analise_json' => $analysis,
                ]);
            } else {
                $storedPath = $service->storeExampleFile($uploadedFile);
                $service->deleteStoredFile($config->arquivo_exemplo);
                $config->update([
                    'nome' => $validated['nome'],
                    'tipo_documento' => $tipoDocumento,
                    'arquivo_exemplo' => $storedPath,
                    'nome_arquivo_exemplo' => $preview['file_name'],
                    'colunas_detectadas_json' => $preview['columns'],
                    'preview_json' => $preview['rows'],
                    'configuracao_analise_json' => $analysis,
                ]);
            }

            return redirect()->route('empresas.upload_config_update', [$empresa->id, $config->id])->with('status', 'Arquivo lido com sucesso. Agora revise o mapeamento do sistema.');
        }

        $analysisConfig = $config->configuracao_analise_json ?? [];
        $analysisConfig['digital_type'] = $digitalType;
        $analysisConfig['ads_type'] = (string) ($validated['ads_type'] ?? ($analysisConfig['ads_type'] ?? 'meta_ads'));
        $analysisConfig['social_example_kind'] = $socialKind;
        $analysisConfig['crm_origem_paga_contem'] = trim((string) ($validated['crm_origem_paga_contem'] ?? ''));
        $analysisConfig['social_receita_percentual_por_1k_alcance'] = (float) ($validated['social_receita_percentual_por_1k_alcance'] ?? 0);
        $analysisConfig['eventos_receita_percentual_por_1k_alcance'] = (float) ($validated['eventos_receita_percentual_por_1k_alcance'] ?? 0);

        $metricConfig = $this->extractMetricConfig($request, $service, $tipoDocumento, $digitalType);
        $mappingPayload = $this->extractMappingPayload($request, $service, $tipoDocumento, $digitalType);

        $config->update([
            'nome' => $validated['nome'],
            'tipo_documento' => $tipoDocumento,
            'mapeamento_json' => $mappingPayload['mapping'],
            'campos_principais_json' => $mappingPayload['primary'],
            'metricas_painel_json' => $metricConfig,
            'configuracao_analise_json' => $analysisConfig,
        ]);

        return redirect()->route('empresas.upload_config_update', [$empresa->id, $config->id])->with('status', 'Configuração atualizada.');
    }

    public function uploadConfigDelete(Empresa $empresa, ConfiguracaoUploadEmpresa $config)
    {
        $config->delete();
        return redirect()->route('empresas.panels', $empresa->id)->with('status', 'Configuração removida.');
    }

    protected function segmentos(): array
    {
        return [
            'Industria' => 'Indústria',
            'Comercio' => 'Comércio',
            'Servico' => 'Serviço',
            'Tecnologia' => 'Tecnologia',
            'Saude' => 'Saúde',
            'Educacao' => 'Educação',
            'Esporte' => 'Esporte',
            'Imobiliario' => 'Imobiliário',
            'Financeiro' => 'Financeiro',
            'Outro' => 'Outro',
        ];
    }

    protected function prepareEmpresaPayload(array $data, Request $request, EmpresaService $service): array
    {
        $data['redes_sociais_json'] = $service->socialLinksFromTextarea($data['redes_sociais_texto'] ?? '');
        unset($data['redes_sociais_texto']);

        $data['cnpj'] = trim((string) ($data['cnpj'] ?? ''));
        $data['segmento'] = trim((string) ($data['segmento'] ?? ''));
        $data['instagram_profile_url'] = trim((string) ($data['instagram_profile_url'] ?? ''));
        $data['ads_biblioteca_query'] = trim((string) ($data['ads_biblioteca_query'] ?? ''));
        $data['feed_cadencia'] = trim((string) ($data['feed_cadencia'] ?? ''));
        $data['observacoes'] = $data['observacoes'] ?? null;
        $data['seguidores'] = (int) ($data['seguidores'] ?? 0);
        $data['posts_total_publicos'] = (int) ($data['posts_total_publicos'] ?? 0);
        $data['feed_posts_visiveis'] = (int) ($data['feed_posts_visiveis'] ?? 0);
        $data['ativo'] = $request->boolean('ativo');

        return $data;
    }

    protected function buildUploadConfigViewData(Empresa $empresa, ConfiguracaoUploadEmpresa $config, UploadConfigService $service): array
    {
        $analysis = $config->configuracao_analise_json ?? [];
        $documentType = (string) ($config->tipo_documento ?: '');
        $digitalType = (string) ($analysis['digital_type'] ?? 'instagram');
        $adsType = (string) ($analysis['ads_type'] ?? 'meta_ads');
        $socialExampleKind = (string) ($analysis['social_example_kind'] ?? 'posts');
        $socialPreviews = is_array($analysis['social_previews'] ?? null) ? $analysis['social_previews'] : [];

        $metricConfig = $service->normalizeMetricConfig($documentType, $config->metricas_painel_json, $digitalType);
        $metricGroups = [];
        foreach ($service->metricGroups($documentType, $digitalType) as $group) {
            $metricGroups[] = [
                'key' => $group['key'],
                'label' => $group['label'],
                'description' => $group['description'],
                'filter_enabled' => (bool) data_get($metricConfig, "filters.{$group['key']}.enabled", false),
                'metrics' => collect($group['metrics'])->map(fn (array $metric) => [
                    'key' => $metric['key'],
                    'label' => $metric['label'],
                    'table_enabled' => (bool) data_get($metricConfig, "metrics.{$metric['key']}.table", true),
                    'chart_enabled' => (bool) data_get($metricConfig, "metrics.{$metric['key']}.chart", true),
                    'chart_allowed' => $service->metricAllowsChart($documentType, $group['key'], $metric['key'], $digitalType),
                ])->all(),
            ];
        }

        $mappingRows = [];
        $mappingSections = [];
        if ($documentType === 'redes_sociais') {
            foreach ($service->mappingTypesForSocial($digitalType) as $section) {
                $sectionMapping = is_array($config->mapeamento_json[$section['key']] ?? null) ? $config->mapeamento_json[$section['key']] : [];
                $sectionPrimary = is_array($config->campos_principais_json[$section['key']] ?? null) ? $config->campos_principais_json[$section['key']] : [];
                $sectionPreview = is_array($socialPreviews[$section['key']] ?? null) ? $socialPreviews[$section['key']] : [];
                $columns = $sectionPreview['columns'] ?? [];
                $rows = [];
                foreach ($service->fieldSchema($documentType, $digitalType) as $field) {
                    $rows[] = [
                        'key' => $field['key'],
                        'label' => $field['label'],
                        'required' => $field['required'],
                        'selected' => $sectionMapping[$field['key']] ?? '',
                        'primary' => in_array($field['key'], $sectionPrimary, true),
                        'options' => $columns,
                    ];
                }
                $mappingSections[] = [
                    'key' => $section['key'],
                    'label' => $section['label'],
                    'rows' => $rows,
                    'preview_columns' => $sectionPreview['columns'] ?? [],
                    'preview_rows' => $sectionPreview['rows'] ?? [],
                    'file_name' => $sectionPreview['file_name'] ?? '',
                ];
            }
        } else {
            $columns = is_array($config->colunas_detectadas_json) ? $config->colunas_detectadas_json : [];
            $mapping = is_array($config->mapeamento_json) ? $config->mapeamento_json : [];
            $primary = is_array($config->campos_principais_json) ? $config->campos_principais_json : [];
            foreach ($service->fieldSchema($documentType, $digitalType) as $field) {
                $mappingRows[] = [
                    'key' => $field['key'],
                    'label' => $field['label'],
                    'required' => $field['required'],
                    'selected' => $mapping[$field['key']] ?? '',
                    'primary' => in_array($field['key'], $primary, true),
                    'options' => $columns,
                ];
            }
        }

        return [
            'empresa' => $empresa,
            'config' => $config,
            'type_options' => $service->typeOptions(),
            'digital_type_options' => $service->digitalTypeOptions(),
            'ads_type_options' => $service->adsTypeOptions(),
            'document_type' => $documentType,
            'digital_type' => $digitalType,
            'ads_type' => $adsType,
            'social_example_kind' => $socialExampleKind,
            'social_mapping_types' => $service->mappingTypesForSocial($digitalType),
            'metric_groups' => $metricGroups,
            'mapping_rows' => $mappingRows,
            'mapping_sections' => $mappingSections,
            'preview_columns' => is_array($config->colunas_detectadas_json) ? $config->colunas_detectadas_json : [],
            'preview_rows' => is_array($config->preview_json) ? $config->preview_json : [],
            'has_example_file' => filled($config->arquivo_exemplo) || filled($config->nome_arquivo_exemplo),
            'crm_origem_paga_contem' => (string) ($analysis['crm_origem_paga_contem'] ?? ''),
            'social_receita_percentual_por_1k_alcance' => (string) ($analysis['social_receita_percentual_por_1k_alcance'] ?? ''),
            'eventos_receita_percentual_por_1k_alcance' => (string) ($analysis['eventos_receita_percentual_por_1k_alcance'] ?? ''),
        ];
    }

    protected function extractMetricConfig(Request $request, UploadConfigService $service, string $tipoDocumento, ?string $digitalType = null): array
    {
        $metrics = [];
        $filters = [];

        foreach ($service->metricGroups($tipoDocumento, $digitalType) as $group) {
            $filters[$group['key']] = [
                'enabled' => $request->boolean("filter_enabled__{$group['key']}"),
            ];
            foreach ($group['metrics'] as $metric) {
                $chartAllowed = $service->metricAllowsChart($tipoDocumento, $group['key'], $metric['key'], $digitalType);
                $metrics[$metric['key']] = [
                    'table' => $request->boolean("metric_table__{$metric['key']}"),
                    'chart' => $chartAllowed ? $request->boolean("metric_chart__{$metric['key']}") : false,
                ];
            }
        }

        return [
            'metrics' => $metrics,
            'filters' => $filters,
        ];
    }

    protected function extractMappingPayload(Request $request, UploadConfigService $service, string $tipoDocumento, ?string $digitalType = null): array
    {
        if ($tipoDocumento === 'leads_eventos') {
            return ['mapping' => [], 'primary' => []];
        }

        if ($tipoDocumento === 'redes_sociais') {
            $mapping = [];
            $primary = [];
            foreach ($service->mappingTypesForSocial($digitalType ?: 'instagram') as $section) {
                $mapping[$section['key']] = [];
                $primary[$section['key']] = [];
                foreach ($service->fieldSchema($tipoDocumento, $digitalType) as $field) {
                    $selected = trim((string) $request->input("map__{$section['key']}__{$field['key']}", ''));
                    if ($selected !== '') {
                        $mapping[$section['key']][$field['key']] = $selected;
                    }
                    if ($request->boolean("primary__{$section['key']}__{$field['key']}")) {
                        $primary[$section['key']][] = $field['key'];
                    }
                }
            }

            return ['mapping' => $mapping, 'primary' => $primary];
        }

        $mapping = [];
        $primary = [];
        foreach ($service->fieldSchema($tipoDocumento, $digitalType) as $field) {
            $selected = trim((string) $request->input("map__{$field['key']}", ''));
            if ($selected !== '') {
                $mapping[$field['key']] = $selected;
            }
            if ($request->boolean("primary__{$field['key']}")) {
                $primary[] = $field['key'];
            }
        }

        return ['mapping' => $mapping, 'primary' => $primary];
    }
}
