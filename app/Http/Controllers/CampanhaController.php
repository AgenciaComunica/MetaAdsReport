<?php

namespace App\Http\Controllers;

use App\Models\Empresa;
use App\Models\UploadCampanha;
use App\Services\CampanhaService;
use Illuminate\Http\Request;

class CampanhaController extends Controller
{
    public function dashboard(Request $request, CampanhaService $service)
    {
        $dashboardTab = (string) $request->query('tab', '');
        $mesParam = (string) $request->query('mes', '');
        $empresa = Empresa::query()->orderBy('id')->first();

        $ranges = $mesParam ? $service->monthRangesForParam($mesParam) : $service->lastCompleteMonthRanges();
        $mesParam = $mesParam ?: $ranges['current_start']->format('Y-m');

        $currentStart = $ranges['current_start'];
        $currentEnd = $ranges['current_end'];
        $previousStart = $ranges['previous_start'];
        $previousEnd = $ranges['previous_end'];

        $mesesDisponiveis = $service->availableMonths();

        $currentMetrics = $service->metricsQuery($empresa?->id, $currentStart, $currentEnd)->get();
        $previousMetrics = $service->metricsQuery($empresa?->id, $previousStart, $previousEnd)->get();

        $kpis = $service->summarizeMetrics($currentMetrics);
        $campaignRows = $service->campaignTable($currentMetrics);
        $timeline = $service->timelineData($currentMetrics);

        $uploadsList = $empresa
            ? UploadCampanha::query()->where('empresa_id', $empresa->id)->orderByDesc('created_at')->limit(10)->get()
            : collect();

        $visibleTabs = [
            ['key' => 'trafego_pago', 'title' => 'Ads Digital'],
        ];

        $dashboardTab = $dashboardTab ?: $visibleTabs[0]['key'];

        return view('campanhas.dashboard', [
            'empresa' => $empresa,
            'dashboard_tab' => $dashboardTab,
            'visible_dashboard_tabs' => $visibleTabs,
            'active_upload_tab' => null,
            'meses_disponiveis' => $mesesDisponiveis,
            'mes_param' => $mesParam,
            'periodo_anterior_resumo' => $previousStart->format('m/Y'),
            'current_start' => $currentStart,
            'current_end' => $currentEnd,
            'previous_start' => $previousStart,
            'previous_end' => $previousEnd,
            'kpis' => $kpis,
            'campaign_rows' => $campaignRows,
            'timeline' => $timeline,
            'uploads_list' => $uploadsList,
            'traffic_has_data' => $currentMetrics->isNotEmpty(),
        ]);
    }
}
