@extends('layouts.app')

@section('page_title', 'Editar Empresa')

@section('content')
<div class="panel mt-4">
    <h3 class="mb-1">Dados da Empresa</h3>
    <p class="text-muted mb-0">Atualize informações principais e definições gerais.</p>
</div>

<div class="panel mt-4">
    <form method="post" action="{{ route('empresas.update.put', $empresa->id) }}">
        @csrf
        @method('PUT')
        @include('empresas._form')
        <div class="mt-3">
            <button class="btn btn-dark" type="submit">Salvar</button>
            <a href="{{ route('empresas.detail', $empresa->id) }}" class="btn btn-outline-secondary">Voltar</a>
        </div>
    </form>
</div>

<div class="panel mt-4">
    <h3 class="mb-1">Usuários de Acesso</h3>
    <p class="text-muted mb-0">Crie usuários que poderão acessar o sistema.</p>

    <form method="post" action="{{ route('empresas.user_store', $empresa->id) }}" class="mt-3">
        @csrf
        <div class="row g-3">
            <div class="col-md-4">
                <label class="form-label">Nome</label>
                <input type="text" name="name" class="form-control" required>
            </div>
            <div class="col-md-4">
                <label class="form-label">Email</label>
                <input type="email" name="email" class="form-control" required>
            </div>
            <div class="col-md-4">
                <label class="form-label">Senha</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <div class="col-md-4">
                <label class="form-label">Confirmar senha</label>
                <input type="password" name="password_confirmation" class="form-control" required>
            </div>
        </div>
        <div class="mt-3">
            <button class="btn btn-outline-dark" type="submit">Adicionar usuário</button>
        </div>
    </form>

    <div class="table-responsive mt-4">
        <table class="table align-middle">
            <thead><tr><th>Nome</th><th>Email</th><th>Criado em</th></tr></thead>
            <tbody>
                @forelse ($usuarios as $usuario)
                    <tr>
                        <td>{{ $usuario->name }}</td>
                        <td>{{ $usuario->email }}</td>
                        <td>{{ br_datetime($usuario->created_at) }}</td>
                    </tr>
                @empty
                    <tr><td colspan="3">Nenhum usuário cadastrado.</td></tr>
                @endforelse
            </tbody>
        </table>
    </div>
</div>
@endsection
