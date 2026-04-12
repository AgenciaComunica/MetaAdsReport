@extends('layouts.app')

@section('page_title', 'Relatórios')

@section('content')
<div class="panel mt-4">
    <h3 class="mb-3">Relatórios</h3>
    <div class="table-responsive">
        <table class="table align-middle">
            <thead><tr><th>Título</th><th>Criado em</th><th>Ações</th></tr></thead>
            <tbody>
                @forelse ($relatorios as $relatorio)
                    <tr>
                        <td>{{ $relatorio->titulo }}</td>
                        <td>{{ $relatorio->created_at?->format('d/m/Y H:i') }}</td>
                        <td>
                            <a href="{{ route('relatorios.detail', $relatorio->id) }}" class="btn btn-sm btn-outline-dark">Abrir</a>
                        </td>
                    </tr>
                @empty
                    <tr><td colspan="3">Nenhum relatório disponível.</td></tr>
                @endforelse
            </tbody>
        </table>
    </div>
</div>
@endsection
