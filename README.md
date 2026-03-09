# 🐍 DjangoTemplate

Este repositório serve como **boilerplate** para iniciar novos projetos Django de forma rápida, limpa e padronizada.  
Ele já vem configurado com suporte a `.env`, MariaDB/MySQL/Postgres, e ajustes para `templates`, `static` e `media`.

---

## ✨ Recursos incluídos
- Estrutura de projeto já organizada (`project/setup`)
- Configuração de variáveis de ambiente com **python-decouple**
- Suporte a `DATABASE_URL` com **dj-database-url**
- Pastas padrão para **templates**, **static** e **media**
- Configuração de **upload seguro**, limites e logs
- Ajustes de segurança prontos para produção (HSTS, cookies seguros, SSL redirect)
- `.env.example` pronto para copiar
- `.gitignore` otimizado
- **Configurações do VS Code** incluídas (`.vscode/`):
  - Debug do Django com F5
  - Python da venv selecionado automaticamente
  - Auto-format ao salvar

---

## 🚀 Como usar

1. **Clonar este template**
   ```bash
   git clone git@github.com:AgenciaComunica/DjangoTemplate.git
   cd DjangoTemplate
   ```

2. **Criar ambiente virtual**
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

3. **Instalar dependências**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variáveis de ambiente**
   ```bash
   cp .env.example .env
   ```
   Edite o `.env` e defina sua `SECRET_KEY`, `DATABASE_URL`, etc.

5. **Rodar migrações e servidor**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

Acesse: http://127.0.0.1:8000

---

## 📂 Estrutura

```
DjangoTemplate/
│ manage.py
│ requirements.txt
│ .env.example
│ INSTALL.md
│
├── project/
│   └── setup/
│       ├── settings.py
│       ├── urls.py
│       ├── asgi.py
│       └── wsgi.py
│
├── templates/
├── static/
├── media/
└── .vscode/
    ├── settings.json
    └── launch.json
```

---

## 🛠️ Tecnologias
- [Django 5.2.x](https://www.djangoproject.com/)
- [python-decouple](https://pypi.org/project/python-decouple/)
- [dj-database-url](https://pypi.org/project/dj-database-url/)

---

## 🔒 Produção (resumo)
Quando `DEBUG=False`, algumas proteções são ativadas automaticamente, como `SECURE_SSL_REDIRECT`,
cookies seguros e HSTS. Você pode ajustar via `.env`:

```
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=3600
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_REFERRER_POLICY=same-origin
```

---

✅ Agora é só usar este repositório como base e começar a criar seus apps!
