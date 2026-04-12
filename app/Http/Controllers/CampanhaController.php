<?php

namespace App\Http\Controllers;

use App\Models\Empresa;
use App\Services\DashboardService;
use Illuminate\Http\Request;

class CampanhaController extends Controller
{
    public function dashboard(Request $request, DashboardService $service)
    {
        $dashboardTab = (string) $request->query('tab', '');
        $mesParam = (string) $request->query('mes', '');
        $empresa = Empresa::query()->orderBy('id')->first();

        return view('campanhas.dashboard', $service->build($empresa, $dashboardTab, $mesParam));
    }
}
