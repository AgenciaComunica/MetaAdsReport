@extends('layouts.app')

@section('page_title', 'Nova Empresa')

@section('content')
<div class="panel mt-4">
    <form method="post" action="{{ route('empresas.store') }}">
        @csrf
        <div class="mb-3">
            <label class="form-label">Nome</label>
            <input type="text" name="nome" class="form-control" required>
        </div>
        <div class="mb-3">
            <label class="form-label">CNPJ</label>
            <input type="text" name="cnpj" class="form-control">
        </div>
        <div class="mb-3">
            <label class="form-label">Segmento</label>
            <input type="text" name="segmento" class="form-control">
        </div>
        <button class="btn btn-dark" type="submit">Salvar</button>
    </form>
</div>
@endsection
