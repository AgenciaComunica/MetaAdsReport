<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>@yield('title', 'Meta Competitive Report')</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css">
    <link rel="stylesheet" href="{{ asset('css/app.css') }}?v=20260405b">
</head>
<body>
    @auth
    <div class="app-layout" data-app-layout>
        <aside class="app-sidebar" data-app-sidebar>
            <div class="app-sidebar-head">
                <span class="app-sidebar-toggle" aria-hidden="true">
                    <span></span>
                    <span></span>
                    <span></span>
                </span>
                <div class="app-sidebar-body">
                    <a href="{{ route('home') }}" class="app-sidebar-brand">Meta Competitive Report</a>
                    <p class="app-sidebar-subtitle">Meta Ads + inteligência competitiva</p>
                </div>
            </div>
            <nav class="app-sidebar-nav">
                <a class="app-sidebar-link" href="{{ route('campanhas.dashboard') }}">Dashboard</a>
                <a class="app-sidebar-link" href="{{ route('empresas.list') }}">Empresas</a>
            </nav>
        </aside>
        <main class="app-main">
            <header class="topbar">
                <div>
                    <h1 class="page-title">@yield('page_title', 'Meta Competitive Report')</h1>
                    <p class="text-muted mb-0">Fluxo local estruturado para evoluir depois para produção.</p>
                </div>
                <div class="d-flex align-items-center gap-2 flex-wrap">
                    @yield('page_actions')
                    <form method="post" action="{{ route('logout') }}">
                        @csrf
                        <button class="btn btn-outline-secondary" type="submit">Sair</button>
                    </form>
                </div>
            </header>
            @if (session('status'))
                <div class="mt-3">
                    <div class="alert alert-info">{{ session('status') }}</div>
                </div>
            @endif
            @if ($errors->any())
                <div class="mt-3">
                    <div class="alert alert-danger">
                        <ul class="mb-0">
                            @foreach ($errors->all() as $error)
                                <li>{{ $error }}</li>
                            @endforeach
                        </ul>
                    </div>
                </div>
            @endif
            @yield('content')
        </main>
    </div>
    @else
    <main class="container py-5">
        @if (session('status'))
            <div class="mt-3">
                <div class="alert alert-info">{{ session('status') }}</div>
            </div>
        @endif
        @if ($errors->any())
            <div class="mt-3">
                <div class="alert alert-danger">
                    <ul class="mb-0">
                        @foreach ($errors->all() as $error)
                            <li>{{ $error }}</li>
                        @endforeach
                    </ul>
                </div>
            </div>
        @endif
        @yield('content')
    </main>
    @endauth
    <div class="loading-overlay" id="loadingOverlay" aria-hidden="true">
        <div class="loading-modal-card">
            <div class="spinner-border text-light" role="status" aria-hidden="true"></div>
            <h3 class="loading-title" id="loadingOverlayTitle">Processando</h3>
            <p class="loading-text mb-0" id="loadingOverlayText">Aguarde enquanto o sistema conclui esta etapa.</p>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <script src="{{ asset('js/app.js') }}?v=20260405b"></script>
    @yield('extra_js')
</body>
</html>
