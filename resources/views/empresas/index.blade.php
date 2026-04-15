@extends('layouts.app')

@section('page_title', 'Empresas')

@section('content')
<div class="panel mt-4">
    <div class="d-flex justify-content-between align-items-center">
        <h3 class="mb-0">Empresas</h3>
        <a href="{{ route('empresas.create') }}" class="btn btn-dark">Nova empresa</a>
    </div>
    <div class="table-responsive mt-3">
        <table class="table align-middle">
            <thead><tr><th>Nome</th><th>CNPJ</th><th>Segmento</th><th>Ações</th></tr></thead>
            <tbody>
                @forelse ($empresas as $empresa)
                    <tr>
                        <td>{{ $empresa->nome }}</td>
                        <td>{{ $empresa->cnpj }}</td>
                        <td>{{ $empresa->segmento ?: '-' }}</td>
                        <td>
                            <a href="{{ route('empresas.detail', $empresa->id) }}" class="btn btn-sm btn-outline-dark">Abrir</a>
                        </td>
                    </tr>
                @empty
                    <tr><td colspan="4">Nenhuma empresa cadastrada.</td></tr>
                @endforelse
            </tbody>
        </table>
    </div>
</div>
@endsection
