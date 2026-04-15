@extends('layouts.app')

@section('page_title', 'Nova Empresa')

@section('content')
<div class="panel mt-4">
    <form method="post" action="{{ route('empresas.store') }}">
        @csrf
        @include('empresas._form')
        <div class="mt-3">
            <button class="btn btn-dark" type="submit">Salvar</button>
            <a href="{{ route('empresas.list') }}" class="btn btn-outline-secondary">Cancelar</a>
        </div>
    </form>
</div>
@endsection
