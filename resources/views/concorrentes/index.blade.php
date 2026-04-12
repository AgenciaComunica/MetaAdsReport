@extends('layouts.app')

@section('page_title', 'Concorrentes')

@section('content')
<div class="panel mt-4">
    <div class="d-flex justify-content-between align-items-center">
        <h3 class="mb-0">Concorrentes</h3>
        <a href="{{ route('concorrentes.create') }}" class="btn btn-dark">Novo Concorrente</a>
    </div>
    <div class="table-responsive mt-3">
        <table class="table align-middle">
            <thead><tr><th>Concorrente</th><th>Plataforma</th><th>Ações</th></tr></thead>
            <tbody>
                @forelse ($concorrentes as $concorrente)
                    <tr>
                        <td>{{ $concorrente->concorrente_nome }}</td>
                        <td>{{ $concorrente->plataforma }}</td>
                        <td>
                            <a href="{{ route('concorrentes.update', $concorrente->id) }}" class="btn btn-sm btn-outline-dark">Editar</a>
                        </td>
                    </tr>
                @empty
                    <tr><td colspan="3">Nenhum concorrente cadastrado.</td></tr>
                @endforelse
            </tbody>
        </table>
    </div>
</div>
@endsection
