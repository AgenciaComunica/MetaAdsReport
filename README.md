# Meta Competitive Report

Sistema web em Django para leitura de campanhas Meta Ads, análise competitiva de concorrentes e geração de relatórios estratégicos com apoio de IA.

## O que já está implementado

- cadastro completo de empresas/clientes
- seleção de empresa ativa no layout
- upload de CSVs do Meta Ads Manager
- normalização automática de colunas com fallback para mapeamento manual
- KPIs e dashboard por período
- comparativo entre períodos
- cadastro e importação de concorrentes via CSV/JSON
- integração com OpenRouter para insights estratégicos
- geração de relatório consolidado em HTML
- exportação PDF com WeasyPrint quando a dependência do sistema estiver disponível

## Estrutura do projeto

```text
MetaAdsReport/
├── .env.example
├── README.md
├── requirements.txt
├── scripts/
│   └── run_local_windows.bat
├── static/
├── templates/
└── project/
    ├── manage.py
    ├── core/
    ├── empresas/
    ├── campanhas/
    ├── concorrentes/
    ├── relatorios/
    ├── ia/
    └── setup/
```

## Setup local no Windows

1. Criar e ativar a virtualenv:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
```

2. Instalar dependências:

```bat
pip install -r requirements.txt
```

3. Copiar o arquivo de ambiente:

```bat
copy .env.example .env
```

4. Ajustar o `.env`:

- para ambiente local simples, deixe SQLite
- para MariaDB, troque `DATABASE_URL`
- para IA, configure `OPENROUTER_API_KEY`

5. Rodar migrações:

```bat
python project\manage.py makemigrations
python project\manage.py migrate
```

6. Criar superusuário:

```bat
python project\manage.py createsuperuser
```

7. Subir o servidor:

```bat
python project\manage.py runserver
```

Abra `http://127.0.0.1:8000`.

## Fluxo recomendado de uso

1. cadastrar uma empresa
2. selecionar a empresa ativa no topo
3. importar um CSV do Meta Ads
4. revisar o dashboard e o comparativo de períodos
5. cadastrar ou importar anúncios de concorrentes
6. gerar um relatório estratégico consolidado

## Variáveis de ambiente principais

```env
SECRET_KEY=troque-esta-chave
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
```

## Observações técnicas

- o parser tenta detectar separador, encoding e sinônimos comuns de colunas
- se a coluna de campanha não for identificada, a tela de mapeamento manual é exibida
- a análise competitiva usa apenas dados observáveis/importados dos concorrentes
- o sistema não infere métricas privadas reais como CPC, CTR, leads ou ROAS dos concorrentes
- o PDF depende do WeasyPrint e das libs nativas do sistema operacional

## Ambientes futuros

O projeto já está modularizado para crescer com:

- autenticação por usuário/equipe
- jobs assíncronos para importação
- cache
- storage remoto
- banco relacional de produção
- observabilidade e deploy

