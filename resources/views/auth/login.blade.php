@extends('layouts.app')

@section('content')
<div class="auth-page-wrap">
    <div class="auth-card">
        <div class="auth-logo-wrap">
            <img src="{{ asset('images/logo.png') }}" alt="Logo" class="auth-logo"
                onerror="this.replaceWith(document.getElementById('authLogoFallback'))">
            <span id="authLogoFallback" class="auth-logo-fallback" style="display:none">MCR</span>
        </div>

        <h2 class="auth-title">Bem-vindo de volta</h2>
        <p class="auth-subtitle">Entre com suas credenciais para acessar o painel.</p>

        <form method="post" action="{{ route('login.attempt') }}">
            @csrf
            <div class="mb-3">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-control" value="{{ old('email') }}" required autofocus>
            </div>
            <div class="mb-3">
                <label class="form-label">Senha</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <div class="form-check form-switch mb-4">
                <input class="form-check-input" type="checkbox" role="switch" name="remember" value="1" id="rememberLogin">
                <label class="form-check-label" for="rememberLogin">Manter conectado</label>
            </div>
            <button class="btn btn-primary w-100" type="submit">Entrar</button>
        </form>
    </div>
</div>
@endsection
