@extends('layouts.app')

@section('page_title', 'Entrar')

@section('content')
<div class="row justify-content-center">
    <div class="col-lg-5">
        <div class="panel mt-4">
            <h2 class="mb-1">Acessar plataforma</h2>
            <p class="text-muted mb-4">Entre com seu email e senha para abrir o dashboard.</p>

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
                <button class="btn btn-dark w-100" type="submit">Entrar</button>
            </form>
        </div>
    </div>
</div>
@endsection
