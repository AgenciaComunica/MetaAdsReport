@extends('layouts.app')

@section('page_title', 'Nova Empresa')

@section('content')
<div class="panel mt-4">
    <form method="post" action="{{ route('empresas.store') }}">
        @csrf
        <div class="row g-3">
            <div class="col-md-6">
                <label class="form-label">Nome</label>
                <input type="text" name="nome" class="form-control" required>
            </div>
            <div class="col-md-6">
                <label class="form-label">CNPJ</label>
                <input type="text" name="cnpj" class="form-control">
            </div>
            <div class="col-md-6">
                <label class="form-label">Segmento</label>
                <input type="text" name="segmento" class="form-control">
            </div>
            <div class="col-md-6 d-flex align-items-end">
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" role="switch" name="ativo" value="1" checked>
                    <label class="form-check-label">Empresa ativa</label>
                </div>
            </div>
            <div class="col-12">
                <label class="form-label">Observações</label>
                <textarea name="observacoes" class="form-control" rows="4" placeholder="Anotações gerais sobre a empresa."></textarea>
            </div>
        </div>
        <div class="mt-3">
            <button class="btn btn-dark" type="submit">Salvar</button>
            <a href="{{ route('empresas.list') }}" class="btn btn-outline-secondary">Cancelar</a>
        </div>
    </form>
</div>
@endsection
