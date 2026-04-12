@extends('layouts.app')

@section('page_title', 'Configurar Painel')

@section('content')
<div class="panel mt-4">
    <h3 class="mb-1">{{ $config->nome }}</h3>
    <p class="text-muted mb-0">Configuração básica do painel.</p>
</div>
@endsection
