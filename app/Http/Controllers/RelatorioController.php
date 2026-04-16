<?php

namespace App\Http\Controllers;

use App\Models\Empresa;
use App\Models\Relatorio;
use App\Services\DashboardService;
use Carbon\Carbon;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

class RelatorioController extends Controller
{
    public function index()
    {
        $relatorios = Relatorio::query()->orderByDesc('created_at')->limit(50)->get();
        return view('relatorios.index', compact('relatorios'));
    }

    public function generate(Request $request, DashboardService $dashboardService)
    {
        $data = $request->validate([
            'titulo' => 'required|string|max:255',
            'data_inicio' => 'nullable|date',
            'data_fim' => 'nullable|date',
            'data_inicio_anterior' => 'nullable|date',
            'data_fim_anterior' => 'nullable|date',
            'mes' => 'nullable|integer|min:1|max:12',
            'ano' => 'nullable|integer|min:2000|max:2100',
        ]);

        $empresa = Empresa::query()->orderBy('id')->firstOrFail();
        $mesParam = ! empty($data['mes']) && ! empty($data['ano'])
            ? sprintf('%04d-%02d', (int) $data['ano'], (int) $data['mes'])
            : (isset($data['data_fim']) ? Carbon::parse($data['data_fim'])->format('Y-m') : '');

        $baseData = $dashboardService->build($empresa, '', $mesParam);
        $tabs = [];

        foreach ($baseData['visible_dashboard_tabs'] as $tab) {
            $tabData = $dashboardService->build($empresa, $tab['key'], $mesParam);
            $content = null;
            $panelType = 'dashboard';

            if ($tab['key'] === 'analise_completa') {
                $content = $tabData['analise_completa_tab'];
                $panelType = 'analise_completa';
            } elseif ($tab['key'] === 'concorrentes') {
                $content = $tabData['concorrentes_tab'];
                $panelType = 'concorrentes';
            } else {
                $content = $tabData['active_upload_tab'];
                $panelType = $content['panel_type'] ?? 'dashboard';
            }

            $tabs[] = [
                'key' => $tab['key'],
                'title' => $tab['title'],
                'panel_type' => $panelType,
                'content' => $content,
                'uploads_list' => $tabData['uploads_list'] ?? collect(),
                'panel_uploads_list' => $tabData['panel_uploads_list'] ?? collect(),
                'eventos_painel_list' => $tabData['eventos_painel_list'] ?? collect(),
                'campaign_rows' => $tabData['campaign_rows'] ?? [],
                'relatorios_list' => $tabData['relatorios_list'] ?? collect(),
                'previous_month_label' => $tabData['previous_month_label'] ?? '',
            ];
        }

        $html = view('relatorios.dashboard_export', [
            'empresa' => $empresa,
            'report_title' => $data['titulo'],
            'report_tabs' => $tabs,
            'mes_label' => $baseData['mes_label'] ?? '',
            'periodo_anterior_resumo' => $baseData['periodo_anterior_resumo'] ?? '',
            'periodo_atual_resumo' => $baseData['periodo_atual_resumo'] ?? '',
            'generated_at' => now(),
        ])->render();

        $relatorio = Relatorio::query()->create([
            'empresa_id' => $empresa->id,
            'titulo' => $data['titulo'],
            'periodo_inicio' => $data['data_inicio'] ?? null,
            'periodo_fim' => $data['data_fim'] ?? null,
            'tipo_periodo' => 'mensal',
            'html_renderizado' => $html,
        ]);

        $fileName = Str::slug($data['titulo']) ?: ('relatorio-'.$relatorio->id);

        return response()->streamDownload(function () use ($html) {
            echo $html;
        }, $fileName.'.html', [
            'Content-Type' => 'text/html; charset=UTF-8',
        ]);
    }

    public function show(Relatorio $relatorio)
    {
        return response($relatorio->html_renderizado ?? '', 200, [
            'Content-Type' => 'text/html; charset=UTF-8',
        ]);
    }

    public function htmlExport(Relatorio $relatorio)
    {
        return response($relatorio->html_renderizado ?? '');
    }

    public function destroy(Relatorio $relatorio)
    {
        $relatorio->delete();
        return redirect()->route('relatorios.list')->with('status', 'Relatório removido.');
    }
}
