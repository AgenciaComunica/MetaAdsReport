<?php

namespace App\Http\Controllers;

use App\Models\Relatorio;
use Illuminate\Http\Request;

class RelatorioController extends Controller
{
    public function index()
    {
        $relatorios = Relatorio::query()->orderByDesc('created_at')->limit(50)->get();
        return view('relatorios.index', compact('relatorios'));
    }

    public function generate(Request $request)
    {
        return redirect()->route('relatorios.list')->with('status', 'Geração de relatório pendente de implementação.');
    }

    public function show(Relatorio $relatorio)
    {
        return view('relatorios.show', compact('relatorio'));
    }

    public function htmlExport(Relatorio $relatorio)
    {
        return response($relatorio->html ?? '');
    }

    public function destroy(Relatorio $relatorio)
    {
        $relatorio->delete();
        return redirect()->route('relatorios.list')->with('status', 'Relatório removido.');
    }
}
