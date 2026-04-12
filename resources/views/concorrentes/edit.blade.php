@extends('layouts.app')

@section('page_title', 'Editar Concorrente')

@section('content')
<div class="panel mt-4">
    <form method="post" action="{{ route('concorrentes.update.put', $concorrente->id) }}">
        @csrf
        @method('PUT')
        <div class="mb-3">
            <label class="form-label">Nome</label>
            <input type="text" name="concorrente_nome" class="form-control" value="{{ $concorrente->concorrente_nome }}" required>
        </div>
        <button class="btn btn-dark" type="submit">Salvar</button>
    </form>
</div>
@endsection
