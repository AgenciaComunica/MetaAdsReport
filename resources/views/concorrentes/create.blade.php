@extends('layouts.app')

@section('page_title', 'Novo Concorrente')

@section('content')
<div class="panel mt-4">
    <form method="post" action="{{ route('concorrentes.store') }}">
        @csrf
        <div class="mb-3">
            <label class="form-label">Empresa ID</label>
            <input type="number" name="empresa_id" class="form-control" required>
        </div>
        <div class="mb-3">
            <label class="form-label">Nome</label>
            <input type="text" name="concorrente_nome" class="form-control" required>
        </div>
        <button class="btn btn-dark" type="submit">Salvar</button>
    </form>
</div>
@endsection
