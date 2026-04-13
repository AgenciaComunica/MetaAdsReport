<?php

namespace App\Http\Controllers;

use App\Models\Empresa;
use App\Models\ConfiguracaoUploadEmpresa;
use App\Models\User;
use App\Services\EmpresaService;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;

class EmpresaController extends Controller
{
    public function index()
    {
        $empresas = Empresa::query()->orderBy('id')->get();
        return view('empresas.index', compact('empresas'));
    }

    public function create()
    {
        return view('empresas.create');
    }

    public function store(Request $request)
    {
        $data = $request->validate([
            'nome' => 'required|string|max:255',
            'cnpj' => 'nullable|string|max:50',
            'segmento' => 'nullable|string|max:100',
            'observacoes' => 'nullable|string',
            'ativo' => 'nullable|boolean',
        ]);
        $data['ativo'] = $request->boolean('ativo');
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

    public function edit(Empresa $empresa)
    {
        $usuarios = User::query()->orderBy('id')->get();
        return view('empresas.edit', compact('empresa', 'usuarios'));
    }

    public function update(Request $request, Empresa $empresa)
    {
        $data = $request->validate([
            'nome' => 'required|string|max:255',
            'cnpj' => 'nullable|string|max:50',
            'segmento' => 'nullable|string|max:100',
            'observacoes' => 'nullable|string',
            'ativo' => 'nullable|boolean',
        ]);
        $data['ativo'] = $request->boolean('ativo');
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
        return redirect()->route('empresas.detail', $empresa->id)->with('status', 'Configuração criada com sucesso.');
    }

    public function uploadConfigEdit(Empresa $empresa, ConfiguracaoUploadEmpresa $config)
    {
        return view('empresas.upload_config', compact('empresa', 'config'));
    }

    public function uploadConfigUpdate(Request $request, Empresa $empresa, ConfiguracaoUploadEmpresa $config)
    {
        $data = $request->validate([
            'nome' => 'required|string|max:255',
            'tipo_documento' => 'nullable|string|max:50',
        ]);
        $config->update($data);
        return redirect()->route('empresas.upload_config_update', [$empresa->id, $config->id])->with('status', 'Configuração atualizada.');
    }

    public function uploadConfigDelete(Empresa $empresa, ConfiguracaoUploadEmpresa $config)
    {
        $config->delete();
        return redirect()->route('empresas.detail', $empresa->id)->with('status', 'Configuração removida.');
    }
}
