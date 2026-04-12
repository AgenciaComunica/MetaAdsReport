<?php

namespace App\Http\Controllers;

use App\Models\ConcorrenteAd;
use App\Services\ConcorrenteService;
use Illuminate\Http\Request;

class ConcorrenteController extends Controller
{
    public function index()
    {
        $concorrentes = ConcorrenteAd::query()->orderByDesc('created_at')->limit(100)->get();
        return view('concorrentes.index', compact('concorrentes'));
    }

    public function create()
    {
        return view('concorrentes.create');
    }

    public function store(Request $request)
    {
        $data = $request->validate([
            'empresa_id' => 'required|integer',
            'concorrente_nome' => 'required|string|max:255',
            'texto_principal' => 'nullable|string',
            'titulo' => 'nullable|string',
            'descricao' => 'nullable|string',
            'cta' => 'nullable|string',
            'plataforma' => 'nullable|string',
            'link' => 'nullable|string',
            'categoria' => 'nullable|string',
            'observacoes' => 'nullable|string',
        ]);
        ConcorrenteAd::create($data);
        return redirect()->route('concorrentes.list')->with('status', 'Concorrente cadastrado.');
    }

    public function edit(ConcorrenteAd $concorrente)
    {
        return view('concorrentes.edit', compact('concorrente'));
    }

    public function update(Request $request, ConcorrenteAd $concorrente)
    {
        $data = $request->validate([
            'concorrente_nome' => 'required|string|max:255',
            'texto_principal' => 'nullable|string',
            'titulo' => 'nullable|string',
            'descricao' => 'nullable|string',
            'cta' => 'nullable|string',
            'plataforma' => 'nullable|string',
            'link' => 'nullable|string',
            'categoria' => 'nullable|string',
            'observacoes' => 'nullable|string',
        ]);
        $concorrente->update($data);
        return redirect()->route('concorrentes.list')->with('status', 'Concorrente atualizado.');
    }

    public function destroy(ConcorrenteAd $concorrente)
    {
        $concorrente->delete();
        return redirect()->route('concorrentes.list')->with('status', 'Concorrente removido.');
    }

    public function import()
    {
        return view('concorrentes.import');
    }

    public function importStore(Request $request)
    {
        return redirect()->route('concorrentes.list')->with('status', 'Importação pendente de implementação.');
    }

    public function instagramImport()
    {
        return view('concorrentes.instagram_import');
    }

    public function instagramImportStore(Request $request)
    {
        return redirect()->route('concorrentes.list')->with('status', 'Importação do Instagram pendente de implementação.');
    }

    public function avaliarAgora(Request $request, ConcorrenteService $service)
    {
        return redirect()->route('concorrentes.list')->with('status', 'Avaliação manual pendente de implementação.');
    }
}
