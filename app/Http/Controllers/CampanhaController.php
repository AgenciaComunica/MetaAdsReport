<?php

namespace App\Http\Controllers;

use App\Models\ConfiguracaoUploadEmpresa;
use App\Models\Empresa;
use App\Models\EventoPainel;
use App\Models\UploadCampanha;
use App\Models\UploadPainel;
use App\Services\CampanhaService;
use App\Services\DashboardService;
use App\Services\UploadConfigService;
use Carbon\Carbon;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Storage;
use PhpOffice\PhpSpreadsheet\Spreadsheet;
use PhpOffice\PhpSpreadsheet\Writer\Xlsx;
use Symfony\Component\HttpFoundation\StreamedResponse;

class CampanhaController extends Controller
{
    public function dashboard(Request $request, DashboardService $service, UploadConfigService $uploadConfigService)
    {
        $dashboardTab = (string) $request->query('tab', '');
        $mesParam = $this->resolveMesParam($request);
        $empresa = Empresa::query()->orderBy('id')->first();
        $viewData = $service->build($empresa, $dashboardTab, $mesParam);

        $viewData['upload_modal'] = null;
        if ($empresa && ! empty($viewData['active_upload_tab']['config_id'])) {
            $config = ConfiguracaoUploadEmpresa::query()->find($viewData['active_upload_tab']['config_id']);
            if ($config) {
                $viewData['upload_modal'] = [
                    'config_id' => $config->id,
                    'config_name' => $config->nome,
                    'panel_type' => $config->tipo_documento,
                    'tab' => $viewData['active_upload_tab']['key'] ?? '',
                    'month' => $request->query('mes'),
                    'year' => $request->query('ano'),
                    'upload_type_options' => $this->uploadTypeOptions($config, $uploadConfigService),
                ];
            }
        }

        return view('campanhas.dashboard', $viewData);
    }

    public function uploadList()
    {
        return redirect()->route('campanhas.dashboard');
    }

    public function uploadCreate(Request $request)
    {
        $empresa = Empresa::query()->with('configuracoes_upload')->orderBy('id')->firstOrFail();
        $config = $this->resolveTargetConfig($request, $empresa);

        if (! $config) {
            return redirect()->route('empresas.panels', $empresa->id)->withErrors([
                'upload' => 'Nenhum painel configurado foi encontrado para receber o upload.',
            ]);
        }

        return redirect()->route('campanhas.dashboard', array_filter([
            'tab' => $request->query('tab') ?: $this->configTabKey($config),
            'mes' => $request->query('mes'),
            'ano' => $request->query('ano'),
        ]));
    }

    public function uploadStore(Request $request, CampanhaService $campanhaService, UploadConfigService $uploadConfigService)
    {
        $empresa = Empresa::query()->with('configuracoes_upload')->orderBy('id')->firstOrFail();
        $config = $this->resolveTargetConfig($request, $empresa);

        if (! $config) {
            return redirect()->route('empresas.panels', $empresa->id)->withErrors([
                'upload' => 'O painel informado não foi encontrado.',
            ]);
        }

        if ($config->tipo_documento === 'leads_eventos') {
            return $this->storeEventUpload($request, $config, $campanhaService);
        }

        $data = $request->validate([
            'config_id' => 'required|integer',
            'arquivo' => 'required|file|mimes:csv,txt,xlsx,xls',
            'tipo_upload' => 'nullable|string|max:50',
            'tab' => 'nullable|string|max:120',
            'mes' => 'nullable',
            'ano' => 'nullable',
        ]);

        if ($config->tipo_documento === 'trafego_pago') {
            return $this->storeTrafficUpload($request, $config, $campanhaService);
        }

        $file = $request->file('arquivo');
        $preview = $uploadConfigService->inspectUploadedFile($file, $file->getClientOriginalName());
        $tipoUpload = $this->sanitizeUploadType((string) ($data['tipo_upload'] ?? 'principal'));
        $storedPath = $file->store('painel-uploads');

        UploadPainel::query()->create([
            'configuracao_id' => $config->id,
            'arquivo' => $storedPath,
            'tipo_upload' => $tipoUpload,
            'nome_arquivo' => $file->getClientOriginalName(),
            'colunas_detectadas_json' => $preview['columns'],
            'preview_json' => $preview['rows'],
        ]);

        return $this->redirectToDashboardTab($request, $config)->with('status', 'Upload enviado com sucesso.');
    }

    public function uploadDetail(UploadCampanha $upload)
    {
        return redirect()->route('campanhas.dashboard')->with('status', 'Detalhe individual de upload ainda não foi migrado. O upload já está disponível no dashboard.');
    }

    public function uploadDelete(UploadCampanha $upload)
    {
        $upload->metricas()->delete();
        $upload->delete();

        return redirect()->route('campanhas.dashboard')->with('status', 'Upload removido com sucesso.');
    }

    public function uploadCampaignDelete(UploadCampanha $upload)
    {
        return $this->uploadDelete($upload);
    }

    public function panelUploadDelete(UploadPainel $upload)
    {
        $config = $upload->configuracao;
        $upload->delete();

        return redirect()->route('campanhas.dashboard', ['tab' => $this->configTabKey($config)])->with('status', 'Upload do painel removido com sucesso.');
    }

    public function eventoPainelDelete(EventoPainel $evento)
    {
        $config = $evento->configuracao;
        $evento->delete();

        return redirect()->route('campanhas.dashboard', ['tab' => $this->configTabKey($config)])->with('status', 'Registro do painel removido com sucesso.');
    }

    public function eventoPainelTemplateDownload(): StreamedResponse
    {
        $spreadsheet = new Spreadsheet();
        $sheet = $spreadsheet->getActiveSheet();
        $sheet->fromArray([
            ['Nome do Evento', 'Data', 'Impacto', 'Leads Alcançados em Média'],
            ['Feira Comercial', '2026-04-10', 'alto', 320],
        ]);

        $writer = new Xlsx($spreadsheet);
        $fileName = 'template-eventos-painel.xlsx';

        return response()->streamDownload(function () use ($writer) {
            $writer->save('php://output');
        }, $fileName, [
            'Content-Type' => 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        ]);
    }

    public function manualMapping(UploadCampanha $upload)
    {
        return redirect()->route('campanhas.dashboard')->with('status', 'O mapeamento manual ainda não foi migrado. Use a configuração do painel para ajustar as colunas.');
    }

    public function manualMappingStore(UploadCampanha $upload)
    {
        return redirect()->route('campanhas.dashboard')->with('status', 'O mapeamento manual ainda não foi migrado. Use a configuração do painel para ajustar as colunas.');
    }

    private function resolveMesParam(Request $request): string
    {
        $mes = (int) $request->query('mes', 0);
        $ano = (int) $request->query('ano', 0);

        if ($mes >= 1 && $mes <= 12 && $ano >= 2000 && $ano <= 2100) {
            return sprintf('%04d-%02d', $ano, $mes);
        }

        return (string) $request->query('mes_param', '');
    }

    private function resolveTargetConfig(Request $request, Empresa $empresa): ?ConfiguracaoUploadEmpresa
    {
        $configId = (int) ($request->query('config') ?: $request->input('config_id', 0));
        if ($configId > 0) {
            return $empresa->configuracoes_upload->firstWhere('id', $configId);
        }

        $tab = (string) ($request->query('tab') ?: $request->input('tab', ''));
        if ($tab !== '') {
            foreach ($empresa->configuracoes_upload as $config) {
                if ($this->configTabKey($config) === $tab) {
                    return $config;
                }
            }
        }

        return $empresa->configuracoes_upload->first();
    }

    private function uploadTypeOptions(ConfiguracaoUploadEmpresa $config, UploadConfigService $uploadConfigService): array
    {
        if ($config->tipo_documento === 'redes_sociais') {
            $digitalType = (string) ($config->configuracao_analise_json['digital_type'] ?? 'instagram');

            return collect($uploadConfigService->mappingTypesForSocial($digitalType))
                ->map(fn (array $item) => ['key' => $item['key'], 'label' => $item['label']])
                ->values()
                ->all();
        }

        return [['key' => 'principal', 'label' => 'Arquivo principal']];
    }

    private function storeTrafficUpload(Request $request, ConfiguracaoUploadEmpresa $config, CampanhaService $campanhaService)
    {
        $file = $request->file('arquivo');
        $storedPath = $file->store('campanhas/uploads');
        $rows = $campanhaService->readTable(Storage::path($storedPath));
        $mapping = $this->trafficImportMapping($config);
        [$startDate, $endDate, $periodType] = $campanhaService->inferUploadPeriodFromDataframe($rows, $mapping, []);

        $upload = UploadCampanha::query()->create([
            'empresa_id' => $config->empresa_id,
            'arquivo' => $storedPath,
            'nome_referencia' => $file->getClientOriginalName(),
            'data_inicio' => $startDate?->toDateString(),
            'data_fim' => $endDate?->toDateString(),
            'periodo_tipo' => $periodType,
            'colunas_mapeadas_json' => $mapping,
        ]);

        $result = $campanhaService->importMetricsFromUpload($upload, $mapping);

        $upload->update([
            'observacoes_importacao' => $result['warnings'] ? implode("\n", $result['warnings']) : null,
            'colunas_mapeadas_json' => $result['mapping'] ?: $mapping,
        ]);

        if (! empty($result['missing_required'])) {
            if ($upload->arquivo && Storage::exists($upload->arquivo)) {
                Storage::delete($upload->arquivo);
            }
            $upload->delete();

            return back()->withErrors([
                'arquivo' => 'Não foi possível importar o arquivo. Ajuste o mapeamento do painel e tente novamente.',
            ])->withInput();
        }

        return $this->redirectToDashboardTab($request, $config)->with('status', 'Upload de Ads Digital importado com sucesso.');
    }

    private function storeEventUpload(Request $request, ConfiguracaoUploadEmpresa $config, CampanhaService $campanhaService)
    {
        $request->validate([
            'config_id' => 'required|integer',
            'arquivo' => 'required|file|mimes:csv,txt,xlsx,xls',
        ]);

        $rows = $campanhaService->readTable($request->file('arquivo')->getRealPath());
        $created = 0;

        foreach ($rows as $row) {
            $normalized = [];
            foreach ($row as $header => $value) {
                $normalized[$this->normalizeHeader((string) $header)] = $value;
            }

            $nomeEvento = trim((string) ($normalized['nome do evento'] ?? $normalized['evento'] ?? ''));
            $dataEvento = $this->parseFlexibleDate($normalized['data'] ?? $normalized['data do evento'] ?? null);
            $impacto = trim((string) ($normalized['impacto'] ?? 'medio'));
            $leadsMedia = (int) ((float) str_replace(',', '.', (string) ($normalized['leads alcancados em media'] ?? $normalized['leads em media'] ?? $normalized['pessoas alcancadas'] ?? 0)));

            if ($nomeEvento === '' || ! $dataEvento) {
                continue;
            }

            EventoPainel::query()->create([
                'configuracao_id' => $config->id,
                'nome_evento' => $nomeEvento,
                'data_evento' => $dataEvento->toDateString(),
                'impacto' => $impacto !== '' ? $impacto : 'medio',
                'leads_media' => $leadsMedia,
            ]);

            $created++;
        }

        return $this->redirectToDashboardTab($request, $config)->with(
            'status',
            $created > 0 ? 'Arquivo de Presença Física importado com sucesso.' : 'Nenhuma linha válida foi encontrada no arquivo enviado.'
        );
    }

    private function trafficImportMapping(ConfiguracaoUploadEmpresa $config): array
    {
        $mapping = is_array($config->mapeamento_json) ? $config->mapeamento_json : [];

        return array_filter([
            'campaign_name' => $mapping['nome_campanha'] ?? null,
            'date' => $mapping['data'] ?? null,
            'amount_spent' => $mapping['valor_usado_brl'] ?? null,
            'impressions' => $mapping['impressoes'] ?? null,
            'reach' => $mapping['alcance'] ?? null,
            'link_clicks' => $mapping['cliques_link'] ?? null,
            'ctr' => $mapping['ctr_todos'] ?? null,
            'cpc' => $mapping['cpc_link'] ?? null,
            'cpm' => $mapping['cpm'] ?? null,
            'results' => $mapping['resultados'] ?? null,
            'inicio_relatorio' => $mapping['inicio_relatorio'] ?? null,
            'fim_relatorio' => $mapping['fim_relatorio'] ?? null,
        ], fn ($value) => filled($value));
    }

    private function redirectToDashboardTab(Request $request, ConfiguracaoUploadEmpresa $config)
    {
        $params = ['tab' => $this->configTabKey($config)];

        $mes = $request->input('mes', $request->query('mes'));
        $ano = $request->input('ano', $request->query('ano'));
        if (filled($mes)) {
            $params['mes'] = $mes;
        }
        if (filled($ano)) {
            $params['ano'] = $ano;
        }

        return redirect()->route('campanhas.dashboard', $params);
    }

    private function configTabKey(ConfiguracaoUploadEmpresa $config): string
    {
        return $config->tipo_documento.'_'.$config->id;
    }

    private function sanitizeUploadType(string $value): string
    {
        $value = trim($value);

        return $value !== '' ? $value : 'principal';
    }

    private function normalizeHeader(string $value): string
    {
        $value = mb_strtolower(trim($value));
        $value = preg_replace('/[^\pL\pN]+/u', ' ', $value) ?? $value;

        return trim($value);
    }

    private function parseFlexibleDate(mixed $value): ?Carbon
    {
        if ($value === null || $value === '') {
            return null;
        }

        foreach (['Y-m-d', 'd/m/Y', 'd-m-Y', 'm/d/Y', 'm-d-Y', 'Y-m-d H:i:s', 'd/m/Y H:i:s'] as $format) {
            try {
                return Carbon::createFromFormat($format, trim((string) $value));
            } catch (\Throwable) {
            }
        }

        try {
            return Carbon::parse((string) $value);
        } catch (\Throwable) {
            return null;
        }
    }
}
