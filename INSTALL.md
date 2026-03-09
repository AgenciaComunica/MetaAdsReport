# 🚀 DjangoTemplate — Guia de Instalação

Este repositório serve como **boilerplate** para iniciar novos projetos Django de forma rápida e padronizada.  

---

## 1. Clonar o repositório

```bash
git clone git@github.com:AgenciaComunica/DjangoTemplate.git
cd DjangoTemplate
```

---

## 2. Criar o ambiente virtual

Use a versão mais recente estável do Python (recomendado **3.12**):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

---

## 3. Instalar dependências

```bash
pip install -r requirements.txt
```

---

## 4. Configurar variáveis de ambiente

Copie o modelo `.env.example` e ajuste conforme o projeto:

```bash
cp .env.example .env
```

Edite o arquivo `.env` para definir:

- SECRET_KEY (gere uma nova chave para cada projeto)  
- Configurações de banco (DATABASE_URL)  
- Configurações de email (se necessário)  
- Hosts e origens confiáveis (ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS)

---

## 5. Criar o banco de dados

Se estiver usando **MariaDB/MySQL**:

```sql
CREATE DATABASE nomedb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'usuario'@'localhost' IDENTIFIED BY 'senha';
GRANT ALL PRIVILEGES ON nomedb.* TO 'usuario'@'localhost';
FLUSH PRIVILEGES;
```

Atualize a DATABASE_URL no `.env`, por exemplo:

```
DATABASE_URL=mysql://usuario:senha@127.0.0.1:3306/nomedb
```

---

## 6. Rodar migrações iniciais

```bash
python manage.py migrate
```

---

## 7. Criar superusuário

```bash
python manage.py createsuperuser
```

---

## 8. Rodar o servidor

```bash
python manage.py runserver
```

Abra em: http://127.0.0.1:8000

---

## 9. Estrutura do projeto

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
└── media/
```

> Dica: quando `DEBUG=False`, algumas configurações de segurança são ativadas
automaticamente (cookies seguros, HSTS, SSL redirect). Ajuste pelo `.env` se necessário.

---

✅ Agora o projeto está pronto para receber seus apps (`apps/core`, `apps/usuarios`, etc.`).
