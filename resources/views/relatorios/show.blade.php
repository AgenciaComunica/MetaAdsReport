@extends('layouts.app')

@section('page_title', 'Relatório')

@section('content')
<div class="panel mt-4">
    <h3 class="mb-2">{{ $relatorio->titulo }}</h3>
    <div class="text-muted">{{ $relatorio->created_at?->format('d/m/Y H:i') }}</div>
    <div class="mt-3">
        {!! $relatorio->html_renderizado !!}
    </div>
</div>
@endsection
