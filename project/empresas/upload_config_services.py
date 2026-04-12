from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from io import BytesIO
from pathlib import Path

import pandas as pd

from .models import ConfiguracaoUploadEmpresa


UPLOAD_FIELD_SCHEMAS = {
    ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO: [
        {'key': 'nome_campanha', 'label': 'Nome da campanha', 'required': True},
        {'key': 'inicio_relatorio', 'label': 'Início do Relatório', 'required': False},
        {'key': 'fim_relatorio', 'label': 'Fim do Relatório', 'required': False},
        {'key': 'anuncios', 'label': 'Anúncios', 'required': False},
        {'key': 'alcance', 'label': 'Alcance', 'required': False},
        {'key': 'impressoes', 'label': 'Impressões', 'required': False},
        {'key': 'tipo_resultado', 'label': 'Tipo de resultado', 'required': False},
        {'key': 'resultados', 'label': 'Resultados', 'required': False},
        {'key': 'valor_usado_brl', 'label': 'Valor usado (BRL)', 'required': True},
        {'key': 'custo_por_resultado', 'label': 'Custo por resultado', 'required': False},
        {'key': 'cliques_link', 'label': 'Cliques no link', 'required': False},
        {'key': 'cpc_link', 'label': 'CPC (custo por clique no link)', 'required': False},
        {'key': 'cpm', 'label': 'CPM (custo por 1.000 impressões)', 'required': False},
        {'key': 'ctr_todos', 'label': 'CTR (todos)', 'required': False},
        {'key': 'visualizacoes', 'label': 'Visualizações', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS: [
        {'key': 'id', 'label': 'ID', 'required': True},
        {'key': 'data_contato', 'label': 'Data do Contato', 'required': True},
        {'key': 'nome_lead', 'label': 'Nome do Lead', 'required': True},
        {'key': 'informacao_contato', 'label': 'Informação do Contato', 'required': False},
        {'key': 'ads_parametros_url', 'label': 'Ads (Parâmetros de URL)', 'required': False},
        {'key': 'canal', 'label': 'Canal', 'required': False},
        {'key': 'valor_venda', 'label': 'Valor da Venda', 'required': False},
        {'key': 'vendedor', 'label': 'Vendedor', 'required': False},
        {'key': 'tag_lead', 'label': 'Tag Lead', 'required': False},
        {'key': 'status_fechamento', 'label': 'Status Fechamento', 'required': False},
        {'key': 'origem_lead', 'label': 'Origem do Lead', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS: [],
    ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS: [
        {'key': 'id_publicacao', 'label': 'ID da Publicação', 'required': True},
        {'key': 'data_publicacao', 'label': 'Data de Publicação', 'required': True},
        {'key': 'tipo_conteudo', 'label': 'Tipo de Conteúdo', 'required': False},
        {'key': 'descricao', 'label': 'Descrição', 'required': False},
        {'key': 'link_permanente', 'label': 'Link Permanente', 'required': False},
        {'key': 'visualizacoes', 'label': 'Visualizações', 'required': False},
        {'key': 'alcance', 'label': 'Alcance', 'required': False},
        {'key': 'curtidas', 'label': 'Curtidas', 'required': False},
        {'key': 'compartilhamentos', 'label': 'Compartilhamentos', 'required': False},
        {'key': 'comentarios', 'label': 'Comentários', 'required': False},
        {'key': 'salvamentos', 'label': 'Salvamentos', 'required': False},
        {'key': 'respostas', 'label': 'Respostas', 'required': False},
        {'key': 'cliques_link', 'label': 'Cliques no Link', 'required': False},
        {'key': 'visitas_perfil', 'label': 'Visitas ao Perfil', 'required': False},
        {'key': 'navegacao', 'label': 'Navegação', 'required': False},
        {'key': 'toques_figurinha', 'label': 'Toques em Figurinhas', 'required': False},
        {'key': 'seguimentos', 'label': 'Seguimentos', 'required': False},
    ],
}

SOCIAL_DIGITAL_FIELD_SCHEMAS = {
    'instagram': UPLOAD_FIELD_SCHEMAS[ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS],
    'facebook': [
        {'key': 'id_publicacao', 'label': 'ID da Publicação', 'required': True},
        {'key': 'data_publicacao', 'label': 'Data de Publicação', 'required': True},
        {'key': 'tipo_conteudo', 'label': 'Tipo de Conteúdo', 'required': False},
        {'key': 'descricao', 'label': 'Descrição', 'required': False},
        {'key': 'link_permanente', 'label': 'Link Permanente', 'required': False},
        {'key': 'visualizacoes', 'label': 'Visualizações', 'required': False},
        {'key': 'alcance', 'label': 'Alcance', 'required': False},
        {'key': 'curtidas', 'label': 'Curtidas / Reações', 'required': False},
        {'key': 'compartilhamentos', 'label': 'Compartilhamentos', 'required': False},
        {'key': 'comentarios', 'label': 'Comentários', 'required': False},
        {'key': 'cliques_link', 'label': 'Cliques no Link', 'required': False},
        {'key': 'seguimentos', 'label': 'Seguimentos', 'required': False},
    ],
    'tiktok': [
        {'key': 'id_publicacao', 'label': 'ID do Conteúdo', 'required': True},
        {'key': 'data_publicacao', 'label': 'Data de Publicação', 'required': True},
        {'key': 'tipo_conteudo', 'label': 'Tipo de Conteúdo', 'required': False},
        {'key': 'descricao', 'label': 'Descrição', 'required': False},
        {'key': 'link_permanente', 'label': 'Link Permanente', 'required': False},
        {'key': 'visualizacoes', 'label': 'Visualizações', 'required': False},
        {'key': 'alcance', 'label': 'Alcance', 'required': False},
        {'key': 'curtidas', 'label': 'Curtidas', 'required': False},
        {'key': 'compartilhamentos', 'label': 'Compartilhamentos', 'required': False},
        {'key': 'comentarios', 'label': 'Comentários', 'required': False},
        {'key': 'salvamentos', 'label': 'Salvamentos', 'required': False},
        {'key': 'visitas_perfil', 'label': 'Visitas ao Perfil', 'required': False},
        {'key': 'seguimentos', 'label': 'Seguimentos', 'required': False},
    ],
    'x': [
        {'key': 'id_publicacao', 'label': 'ID da Publicação', 'required': True},
        {'key': 'data_publicacao', 'label': 'Data da Publicação', 'required': True},
        {'key': 'tipo_conteudo', 'label': 'Tipo de Conteúdo', 'required': False},
        {'key': 'descricao', 'label': 'Texto do Post', 'required': False},
        {'key': 'link_permanente', 'label': 'Link Permanente', 'required': False},
        {'key': 'visualizacoes', 'label': 'Impressões', 'required': False},
        {'key': 'alcance', 'label': 'Alcance', 'required': False},
        {'key': 'curtidas', 'label': 'Curtidas', 'required': False},
        {'key': 'compartilhamentos', 'label': 'Reposts / Compartilhamentos', 'required': False},
        {'key': 'comentarios', 'label': 'Respostas', 'required': False},
        {'key': 'cliques_link', 'label': 'Cliques no Link', 'required': False},
        {'key': 'visitas_perfil', 'label': 'Visitas ao Perfil', 'required': False},
        {'key': 'seguimentos', 'label': 'Seguimentos', 'required': False},
    ],
    'website': [
        {'key': 'id_publicacao', 'label': 'Página / Landing Page', 'required': True},
        {'key': 'data_publicacao', 'label': 'Data', 'required': True},
        {'key': 'descricao', 'label': 'Título / Página', 'required': False},
        {'key': 'link_permanente', 'label': 'URL', 'required': False},
        {'key': 'usuarios', 'label': 'Usuários', 'required': False},
        {'key': 'novos_usuarios', 'label': 'Novos Usuários', 'required': False},
        {'key': 'sessoes', 'label': 'Sessões', 'required': False},
        {'key': 'sessoes_engajadas', 'label': 'Sessões Engajadas', 'required': False},
        {'key': 'visualizacoes_pagina', 'label': 'Visualizações de Página', 'required': False},
        {'key': 'taxa_engajamento', 'label': 'Taxa de Engajamento', 'required': False},
        {'key': 'conversoes', 'label': 'Conversões', 'required': False},
    ],
    'outro': [
        {'key': 'id_publicacao', 'label': 'ID do Conteúdo', 'required': True},
        {'key': 'data_publicacao', 'label': 'Data de Publicação', 'required': True},
        {'key': 'tipo_conteudo', 'label': 'Tipo de Conteúdo', 'required': False},
        {'key': 'descricao', 'label': 'Descrição', 'required': False},
        {'key': 'link_permanente', 'label': 'Link Permanente', 'required': False},
        {'key': 'visualizacoes', 'label': 'Visualizações', 'required': False},
        {'key': 'alcance', 'label': 'Alcance', 'required': False},
        {'key': 'curtidas', 'label': 'Curtidas', 'required': False},
        {'key': 'compartilhamentos', 'label': 'Compartilhamentos', 'required': False},
        {'key': 'comentarios', 'label': 'Comentários', 'required': False},
        {'key': 'cliques_link', 'label': 'Cliques no Link', 'required': False},
        {'key': 'visitas_perfil', 'label': 'Visitas ao Perfil', 'required': False},
        {'key': 'seguimentos', 'label': 'Seguimentos', 'required': False},
    ],
}

SOCIAL_FIXED_HEADER_MAPPINGS = {
    'instagram': {
        'posts': {
            'id_publicacao': ['Identificação do post'],
            'data_publicacao': ['Horário de publicação'],
            'tipo_conteudo': ['Tipo de post'],
            'descricao': ['Descrição'],
            'link_permanente': ['Link permanente'],
            'visualizacoes': ['Visualizações'],
            'alcance': ['Alcance'],
            'curtidas': ['Curtidas'],
            'compartilhamentos': ['Compartilhamentos'],
            'comentarios': ['Comentários'],
            'salvamentos': ['Salvamentos'],
            'seguimentos': ['Seguimentos'],
        },
        'stories': {
            'id_publicacao': ['Identificação do post'],
            'data_publicacao': ['Horário de publicação'],
            'tipo_conteudo': ['Tipo de post'],
            'descricao': ['Descrição'],
            'link_permanente': ['Link permanente'],
            'visualizacoes': ['Visualizações'],
            'alcance': ['Alcance'],
            'curtidas': ['Curtidas'],
            'compartilhamentos': ['Compartilhamentos'],
            'respostas': ['Respostas'],
            'cliques_link': ['Cliques no link'],
            'visitas_perfil': ['Visitas ao perfil'],
            'navegacao': ['Navegação'],
            'toques_figurinha': ['Toques em figurinhas'],
            'seguimentos': ['Seguimentos'],
        },
    },
    'website': {
        'principal': {
            'id_publicacao': ['Landing page', 'Página de destino', 'Page path + query string'],
            'data_publicacao': ['Data'],
            'descricao': ['Título da página', 'Page title', 'Título'],
            'link_permanente': ['Landing page', 'Page path + query string', 'URL'],
            'usuarios': ['Usuários', 'Usuários ativos', 'Active users'],
            'novos_usuarios': ['Novos usuários', 'New users'],
            'sessoes': ['Sessões', 'Sessions'],
            'sessoes_engajadas': ['Sessões engajadas', 'Engaged sessions'],
            'visualizacoes_pagina': ['Visualizações', 'Views', 'Visualizações de página', 'Page views'],
            'taxa_engajamento': ['Taxa de engajamento', 'Engagement rate'],
            'conversoes': ['Conversões', 'Key events', 'Eventos principais'],
        },
    },
}

PANEL_METRIC_SCHEMAS = {
    ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO: [
        {'key': 'investimento', 'label': 'Investimento'},
        {'key': 'cpm', 'label': 'CPM'},
        {'key': 'cpc', 'label': 'CPC'},
        {'key': 'cpl', 'label': 'CPL'},
        {'key': 'impressoes', 'label': 'Impressões'},
        {'key': 'alcance', 'label': 'Alcance'},
        {'key': 'ctr', 'label': 'CTR'},
        {'key': 'taxa_conversao', 'label': 'Taxa de Conversão'},
        {'key': 'frequencia', 'label': 'Frequência'},
        {'key': 'score_relevancia', 'label': 'Score de Relevância'},
        {'key': 'cpm_relativo', 'label': 'CPM Relativo'},
        {'key': 'resultado_principal', 'label': 'Resultado Principal'},
        {'key': 'custo_por_resultado', 'label': 'Custo por Resultado'},
        {'key': 'taxa_resposta', 'label': 'Taxa de Resposta'},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS: [
        {'key': 'receita_total', 'label': 'Receita Total'},
        {'key': 'vendas_concluidas', 'label': 'Vendas Concluídas'},
        {'key': 'taxa_conversao', 'label': 'Taxa de Conversão'},
        {'key': 'conversas', 'label': 'Conversas'},
        {'key': 'ticket_medio', 'label': 'Ticket Médio'},
        {'key': 'receita_marketing_pago', 'label': 'Marketing Pago'},
        {'key': 'receita_marketing_organico', 'label': 'Marketing Orgânico'},
        {'key': 'receita_operacional', 'label': 'Operacional'},
        {'key': 'receita_sem_categoria', 'label': 'Sem categoria'},
        {'key': 'status_fechamento', 'label': 'Status do Fechamento'},
        {'key': 'temperatura_lead', 'label': 'Temperatura do Lead'},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS: [
        {'key': 'eventos_total', 'label': 'Eventos'},
        {'key': 'participantes_total', 'label': 'Pessoas Alcançadas'},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS: [
        {'key': 'quantidade_publicacoes', 'label': 'Quantidade de Publicações'},
        {'key': 'visualizacoes', 'label': 'Visualizações'},
        {'key': 'alcance', 'label': 'Alcance'},
        {'key': 'curtidas', 'label': 'Curtidas'},
        {'key': 'compartilhamentos', 'label': 'Compartilhamentos'},
        {'key': 'quantidade_posts', 'label': 'Quantidade de Posts'},
        {'key': 'visualizacoes_posts', 'label': 'Visualizações dos Posts'},
        {'key': 'alcance_posts', 'label': 'Alcance dos Posts'},
        {'key': 'curtidas_posts', 'label': 'Curtidas dos Posts'},
        {'key': 'compartilhamentos_posts', 'label': 'Compartilhamentos dos Posts'},
        {'key': 'quantidade_stories', 'label': 'Quantidade de Stories'},
        {'key': 'visualizacoes_stories', 'label': 'Visualizações dos Stories'},
        {'key': 'alcance_stories', 'label': 'Alcance dos Stories'},
        {'key': 'curtidas_stories', 'label': 'Curtidas dos Stories'},
        {'key': 'compartilhamentos_stories', 'label': 'Compartilhamentos dos Stories'},
        {'key': 'comentarios', 'label': 'Comentários'},
        {'key': 'salvamentos', 'label': 'Salvamentos'},
        {'key': 'respostas', 'label': 'Respostas'},
        {'key': 'cliques_link', 'label': 'Cliques no Link'},
        {'key': 'visitas_perfil', 'label': 'Visitas ao Perfil'},
    ],
}

SOCIAL_DIGITAL_METRIC_SCHEMAS = {
    'instagram': PANEL_METRIC_SCHEMAS[ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS],
    'facebook': [
        {'key': 'quantidade_publicacoes', 'label': 'Quantidade de Publicações'},
        {'key': 'visualizacoes', 'label': 'Visualizações'},
        {'key': 'alcance', 'label': 'Alcance'},
        {'key': 'curtidas', 'label': 'Curtidas / Reações'},
        {'key': 'compartilhamentos', 'label': 'Compartilhamentos'},
        {'key': 'comentarios', 'label': 'Comentários'},
        {'key': 'cliques_link', 'label': 'Cliques no Link'},
        {'key': 'seguimentos', 'label': 'Seguimentos'},
    ],
    'tiktok': [
        {'key': 'quantidade_publicacoes', 'label': 'Quantidade de Conteúdos'},
        {'key': 'visualizacoes', 'label': 'Visualizações'},
        {'key': 'alcance', 'label': 'Alcance'},
        {'key': 'curtidas', 'label': 'Curtidas'},
        {'key': 'compartilhamentos', 'label': 'Compartilhamentos'},
        {'key': 'comentarios', 'label': 'Comentários'},
        {'key': 'salvamentos', 'label': 'Salvamentos'},
        {'key': 'visitas_perfil', 'label': 'Visitas ao Perfil'},
        {'key': 'seguimentos', 'label': 'Seguimentos'},
    ],
    'x': [
        {'key': 'quantidade_publicacoes', 'label': 'Quantidade de Posts'},
        {'key': 'visualizacoes', 'label': 'Impressões'},
        {'key': 'alcance', 'label': 'Alcance'},
        {'key': 'curtidas', 'label': 'Curtidas'},
        {'key': 'compartilhamentos', 'label': 'Reposts / Compartilhamentos'},
        {'key': 'comentarios', 'label': 'Respostas'},
        {'key': 'cliques_link', 'label': 'Cliques no Link'},
        {'key': 'visitas_perfil', 'label': 'Visitas ao Perfil'},
        {'key': 'seguimentos', 'label': 'Seguimentos'},
    ],
    'website': [
        {'key': 'usuarios', 'label': 'Usuários'},
        {'key': 'novos_usuarios', 'label': 'Novos Usuários'},
        {'key': 'sessoes', 'label': 'Sessões'},
        {'key': 'sessoes_engajadas', 'label': 'Sessões Engajadas'},
        {'key': 'visualizacoes_pagina', 'label': 'Visualizações de Página'},
        {'key': 'taxa_engajamento', 'label': 'Taxa de Engajamento'},
        {'key': 'conversoes', 'label': 'Conversões'},
    ],
    'outro': [
        {'key': 'quantidade_publicacoes', 'label': 'Quantidade de Conteúdos'},
        {'key': 'visualizacoes', 'label': 'Visualizações'},
        {'key': 'alcance', 'label': 'Alcance'},
        {'key': 'curtidas', 'label': 'Curtidas'},
        {'key': 'compartilhamentos', 'label': 'Compartilhamentos'},
        {'key': 'comentarios', 'label': 'Comentários'},
        {'key': 'cliques_link', 'label': 'Cliques no Link'},
        {'key': 'visitas_perfil', 'label': 'Visitas ao Perfil'},
        {'key': 'seguimentos', 'label': 'Seguimentos'},
    ],
}

LEGACY_TYPE_MAP = {
    'crm': ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS,
    'vendas': ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS,
    'leads': ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS,
    'eventos': ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS,
}


LEGACY_FIELD_SCHEMAS = {
    'crm': UPLOAD_FIELD_SCHEMAS[ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS],
    'vendas': UPLOAD_FIELD_SCHEMAS[ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS],
    'leads': UPLOAD_FIELD_SCHEMAS[ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS],
    'eventos': UPLOAD_FIELD_SCHEMAS[ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS],
    'financeiro': [
        {'key': 'lancamento_id', 'label': 'Lançamento / ID', 'required': True},
        {'key': 'data_competencia', 'label': 'Data de Competência', 'required': True},
        {'key': 'categoria', 'label': 'Categoria', 'required': True},
        {'key': 'descricao', 'label': 'Descrição', 'required': False},
        {'key': 'centro_custo', 'label': 'Centro de Custo', 'required': False},
        {'key': 'valor', 'label': 'Valor', 'required': True},
        {'key': 'status', 'label': 'Status', 'required': False},
    ],
    'estoque': [
        {'key': 'sku', 'label': 'SKU', 'required': True},
        {'key': 'produto', 'label': 'Produto', 'required': True},
        {'key': 'categoria', 'label': 'Categoria', 'required': False},
        {'key': 'quantidade', 'label': 'Quantidade', 'required': True},
        {'key': 'local', 'label': 'Local', 'required': False},
        {'key': 'custo_unitario', 'label': 'Custo Unitário', 'required': False},
        {'key': 'atualizado_em', 'label': 'Atualizado em', 'required': False},
    ],
    'atendimento': [
        {'key': 'protocolo', 'label': 'Protocolo', 'required': True},
        {'key': 'cliente', 'label': 'Cliente', 'required': False},
        {'key': 'canal', 'label': 'Canal', 'required': False},
        {'key': 'assunto', 'label': 'Assunto', 'required': True},
        {'key': 'data_abertura', 'label': 'Data de Abertura', 'required': True},
        {'key': 'status', 'label': 'Status', 'required': False},
        {'key': 'responsavel', 'label': 'Responsável', 'required': False},
        {'key': 'sla', 'label': 'SLA', 'required': False},
    ],
}

UPLOAD_TYPE_CHOICES = list(ConfiguracaoUploadEmpresa.TipoDocumento.choices)
TRAFFIC_PANEL_CATEGORY_DEFINITIONS = [
    {
        'key': 'resultados',
        'label': 'Resultados',
        'description': 'Bloco principal de conversão, preparado para múltiplas plataformas e objetivos.',
        'metrics': ['resultado_principal', 'custo_por_resultado', 'taxa_resposta'],
    },
    {
        'key': 'custo_investimento',
        'label': 'Custo e Investimento',
        'description': 'Controle financeiro do período e eficiência básica do investimento.',
        'metrics': ['investimento', 'cpm', 'cpc', 'cpl'],
    },
    {
        'key': 'performance_anuncios',
        'label': 'Performance dos Anúncios',
        'description': 'Entrega, alcance e capacidade de gerar ação ao longo do funil.',
        'metrics': ['impressoes', 'alcance', 'ctr', 'taxa_conversao', 'frequencia'],
    },
    {
        'key': 'qualidade_relevancia',
        'label': 'Qualidade e Relevância',
        'description': 'Leitura sintética da saúde do criativo e da pressão de mídia.',
        'metrics': ['score_relevancia', 'cpm_relativo'],
    },
]
TRAFFIC_METRIC_TOOLTIPS = {
    'investimento': 'Valor total investido em mídia no período selecionado.',
    'cpm': 'Custo médio para cada mil impressões entregues.',
    'cpc': 'Custo médio por clique gerado pelos anúncios.',
    'cpl': 'Custo por lead ou custo por resultado principal captado.',
    'impressoes': 'Quantidade total de exibições dos anúncios.',
    'alcance': 'Quantidade de pessoas únicas alcançadas.',
    'ctr': 'Percentual de cliques em relação às impressões.',
    'taxa_conversao': 'Percentual de resultados em relação aos cliques.',
    'frequencia': 'Média de vezes que cada pessoa impactada viu o anúncio.',
    'score_relevancia': 'Indicador sintético calculado com base em CTR, CPM, CPC e frequência.',
    'cpm_relativo': 'Compara o CPM atual com o período anterior. Abaixo de 1,00x é melhor.',
    'resultado_principal': 'Conversão principal do painel, genérica e preparada para diferentes objetivos.',
    'custo_por_resultado': 'Custo médio por conversão principal obtida.',
    'taxa_resposta': 'Percentual de respostas ou conversões em relação aos cliques gerados.',
}
CRM_PANEL_CATEGORY_DEFINITIONS = [
    {
        'key': 'resultado',
        'label': 'Resultado',
        'description': 'Indicadores principais do comercial com comparativo entre períodos.',
        'metrics': ['receita_total', 'vendas_concluidas', 'taxa_conversao', 'conversas', 'ticket_medio'],
    },
    {
        'key': 'origem',
        'label': 'Origem',
        'description': 'Distribuição da receita entre marketing pago, marketing orgânico, operação e itens sem categoria.',
        'metrics': ['receita_marketing_pago', 'receita_marketing_organico', 'receita_operacional', 'receita_sem_categoria'],
    },
    {
        'key': 'temperatura',
        'label': 'Temperatura Leads',
        'description': 'Distribuição por tags/temperatura dos leads e comparativo entre períodos.',
        'metrics': ['temperatura_lead'],
    },
]
CRM_METRIC_TOOLTIPS = {
    'receita_total': 'Soma total do valor vendido no período.',
    'vendas_concluidas': 'Quantidade de vendas fechadas no período.',
    'taxa_conversao': 'Conversão entre conversas e vendas concluídas.',
    'conversas': 'Total de conversas atendidas no período.',
    'ticket_medio': 'Ticket médio do período.',
    'receita_marketing_pago': 'Receita atribuída ao marketing pago, vinda diretamente do tráfego pago.',
    'receita_marketing_organico': 'Receita atribuída ao marketing orgânico, como Marketing e Google.',
    'receita_operacional': 'Receita atribuída à operação, como Indicação e Cliente Base.',
    'receita_sem_categoria': 'Receita sem classificação conhecida de origem.',
    'temperatura_lead': 'Distribuição das tags/temperatura configuradas no CRM.',
}
SOCIAL_PANEL_CATEGORY_DEFINITIONS = [
    {
        'key': 'visao_geral',
        'label': 'Visão Geral',
        'description': 'Desempenho consolidado do conteúdo orgânico no período.',
        'metrics': ['quantidade_publicacoes', 'visualizacoes', 'alcance', 'curtidas', 'compartilhamentos'],
    },
    {
        'key': 'posts',
        'label': 'Posts',
        'description': 'Desempenho consolidado apenas dos conteúdos do tipo post.',
        'metrics': ['quantidade_posts', 'visualizacoes_posts', 'alcance_posts', 'curtidas_posts', 'compartilhamentos_posts'],
    },
    {
        'key': 'stories',
        'label': 'Stories',
        'description': 'Desempenho consolidado apenas dos conteúdos do tipo story.',
        'metrics': ['quantidade_stories', 'visualizacoes_stories', 'alcance_stories', 'curtidas_stories', 'compartilhamentos_stories'],
    },
    {
        'key': 'engajamento',
        'label': 'Engajamento',
        'description': 'Indicadores complementares de interação e resposta.',
        'metrics': ['curtidas', 'compartilhamentos', 'comentarios', 'salvamentos', 'respostas', 'cliques_link', 'visitas_perfil'],
    },
]
SOCIAL_METRIC_TOOLTIPS = {
    'quantidade_publicacoes': 'Total de publicações válidas importadas no período.',
    'visualizacoes': 'Soma total de visualizações no período.',
    'alcance': 'Soma total de alcance no período.',
    'curtidas': 'Soma total de curtidas no período.',
    'compartilhamentos': 'Soma total de compartilhamentos no período.',
    'quantidade_posts': 'Total de registros classificados como post.',
    'visualizacoes_posts': 'Visualizações apenas de posts.',
    'alcance_posts': 'Alcance apenas de posts.',
    'curtidas_posts': 'Curtidas apenas de posts.',
    'compartilhamentos_posts': 'Compartilhamentos apenas de posts.',
    'quantidade_stories': 'Total de registros classificados como story.',
    'visualizacoes_stories': 'Visualizações apenas de stories.',
    'alcance_stories': 'Alcance apenas de stories.',
    'curtidas_stories': 'Curtidas apenas de stories.',
    'compartilhamentos_stories': 'Compartilhamentos apenas de stories.',
    'comentarios': 'Total de comentários no período.',
    'salvamentos': 'Total de salvamentos no período.',
    'respostas': 'Total de respostas no período.',
    'cliques_link': 'Total de cliques em links no período.',
    'visitas_perfil': 'Total de visitas ao perfil no período.',
}

SOCIAL_DIGITAL_CATEGORY_DEFINITIONS = {
    'instagram': SOCIAL_PANEL_CATEGORY_DEFINITIONS,
    'facebook': [
        {
            'key': 'visao_geral',
            'label': 'Visão Geral',
            'description': 'Desempenho consolidado da presença orgânica no Facebook.',
            'metrics': ['quantidade_publicacoes', 'visualizacoes', 'alcance'],
        },
        {
            'key': 'engajamento',
            'label': 'Engajamento',
            'description': 'Interações principais do conteúdo publicado.',
            'metrics': ['curtidas', 'compartilhamentos', 'comentarios'],
        },
        {
            'key': 'crescimento',
            'label': 'Crescimento',
            'description': 'Sinais de tráfego e crescimento da conta.',
            'metrics': ['cliques_link', 'seguimentos'],
        },
    ],
    'tiktok': [
        {
            'key': 'visao_geral',
            'label': 'Visão Geral',
            'description': 'Desempenho consolidado do conteúdo publicado no TikTok.',
            'metrics': ['quantidade_publicacoes', 'visualizacoes', 'alcance'],
        },
        {
            'key': 'engajamento',
            'label': 'Engajamento',
            'description': 'Interações do conteúdo com a audiência.',
            'metrics': ['curtidas', 'compartilhamentos', 'comentarios', 'salvamentos'],
        },
        {
            'key': 'audiencia',
            'label': 'Audiência',
            'description': 'Sinais de interesse pela conta e crescimento.',
            'metrics': ['visitas_perfil', 'seguimentos'],
        },
    ],
    'x': [
        {
            'key': 'visao_geral',
            'label': 'Visão Geral',
            'description': 'Desempenho consolidado do conteúdo publicado no X.',
            'metrics': ['quantidade_publicacoes', 'visualizacoes', 'alcance'],
        },
        {
            'key': 'interacao',
            'label': 'Interação',
            'description': 'Respostas e compartilhamentos do conteúdo.',
            'metrics': ['curtidas', 'compartilhamentos', 'comentarios'],
        },
        {
            'key': 'trafego',
            'label': 'Tráfego',
            'description': 'Sinais de tráfego gerado e interesse no perfil.',
            'metrics': ['cliques_link', 'visitas_perfil', 'seguimentos'],
        },
    ],
    'website': [
        {
            'key': 'visao_geral',
            'label': 'Visão Geral',
            'description': 'Leitura consolidada do tráfego do website no período.',
            'metrics': ['usuarios', 'sessoes', 'visualizacoes_pagina'],
        },
        {
            'key': 'aquisicao',
            'label': 'Aquisição',
            'description': 'Indicadores de aquisição e qualidade de sessão.',
            'metrics': ['novos_usuarios', 'sessoes_engajadas', 'taxa_engajamento'],
        },
        {
            'key': 'conversao',
            'label': 'Conversão',
            'description': 'Indicadores de conversão e resultado do site.',
            'metrics': ['conversoes'],
        },
    ],
    'outro': [
        {
            'key': 'visao_geral',
            'label': 'Visão Geral',
            'description': 'Desempenho consolidado do conteúdo publicado.',
            'metrics': ['quantidade_publicacoes', 'visualizacoes', 'alcance'],
        },
        {
            'key': 'engajamento',
            'label': 'Engajamento',
            'description': 'Interações principais do conteúdo.',
            'metrics': ['curtidas', 'compartilhamentos', 'comentarios'],
        },
        {
            'key': 'audiencia',
            'label': 'Audiência',
            'description': 'Sinais de tráfego e crescimento.',
            'metrics': ['cliques_link', 'visitas_perfil', 'seguimentos'],
        },
    ],
}

SOCIAL_DIGITAL_METRIC_TOOLTIPS = {
    'instagram': SOCIAL_METRIC_TOOLTIPS,
    'facebook': {
        'quantidade_publicacoes': 'Total de publicações válidas importadas no período.',
        'visualizacoes': 'Total de visualizações do conteúdo no período.',
        'alcance': 'Total de alcance orgânico no período.',
        'curtidas': 'Total de curtidas ou reações no período.',
        'compartilhamentos': 'Total de compartilhamentos no período.',
        'comentarios': 'Total de comentários no período.',
        'cliques_link': 'Total de cliques em links no período.',
        'seguimentos': 'Total de novos seguimentos no período.',
    },
    'tiktok': {
        'quantidade_publicacoes': 'Total de conteúdos válidos importados no período.',
        'visualizacoes': 'Total de visualizações no período.',
        'alcance': 'Total de alcance no período.',
        'curtidas': 'Total de curtidas no período.',
        'compartilhamentos': 'Total de compartilhamentos no período.',
        'comentarios': 'Total de comentários no período.',
        'salvamentos': 'Total de salvamentos no período.',
        'visitas_perfil': 'Total de visitas ao perfil no período.',
        'seguimentos': 'Total de novos seguidores no período.',
    },
    'x': {
        'quantidade_publicacoes': 'Total de posts válidos importados no período.',
        'visualizacoes': 'Total de impressões no período.',
        'alcance': 'Total de alcance no período.',
        'curtidas': 'Total de curtidas no período.',
        'compartilhamentos': 'Total de reposts/compartilhamentos no período.',
        'comentarios': 'Total de respostas no período.',
        'cliques_link': 'Total de cliques em links no período.',
        'visitas_perfil': 'Total de visitas ao perfil no período.',
        'seguimentos': 'Total de novos seguidores no período.',
    },
    'website': {
        'usuarios': 'Usuários totais do website no período.',
        'novos_usuarios': 'Novos usuários no período.',
        'sessoes': 'Sessões totais do website no período.',
        'sessoes_engajadas': 'Sessões engajadas no período.',
        'visualizacoes_pagina': 'Visualizações de página no período.',
        'taxa_engajamento': 'Percentual de sessões engajadas sobre o total de sessões.',
        'conversoes': 'Conversões registradas no período.',
    },
    'outro': {
        'quantidade_publicacoes': 'Total de conteúdos válidos importados no período.',
        'visualizacoes': 'Total de visualizações no período.',
        'alcance': 'Total de alcance no período.',
        'curtidas': 'Total de curtidas no período.',
        'compartilhamentos': 'Total de compartilhamentos no período.',
        'comentarios': 'Total de comentários no período.',
        'cliques_link': 'Total de cliques em links no período.',
        'visitas_perfil': 'Total de visitas ao perfil no período.',
        'seguimentos': 'Total de novos seguimentos no período.',
    },
}


@dataclass
class UploadPreview:
    columns: list[str]
    rows: list[dict]
    file_name: str


def get_field_schema(tipo_documento, variant=None):
    if tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS:
        return SOCIAL_DIGITAL_FIELD_SCHEMAS.get(variant or 'instagram', SOCIAL_DIGITAL_FIELD_SCHEMAS['instagram'])
    if tipo_documento in UPLOAD_FIELD_SCHEMAS:
        return UPLOAD_FIELD_SCHEMAS[tipo_documento]
    return LEGACY_FIELD_SCHEMAS.get(tipo_documento, [])


def get_type_label(tipo_documento):
    return dict(UPLOAD_TYPE_CHOICES).get(tipo_documento, tipo_documento)


def get_default_social_mapping(kind, columns, digital_type='instagram'):
    available = {str(column).strip(): str(column).strip() for column in (columns or [])}
    mapping = {}
    type_mappings = SOCIAL_FIXED_HEADER_MAPPINGS.get(digital_type, {})
    header_map = type_mappings.get(kind, {}) if isinstance(type_mappings, dict) else {}
    if not header_map and kind in SOCIAL_FIXED_HEADER_MAPPINGS:
        header_map = SOCIAL_FIXED_HEADER_MAPPINGS.get(kind, {})
    for field_key, headers in header_map.items():
        candidates = headers if isinstance(headers, list) else [headers]
        for header in candidates:
            if header in available:
                mapping[field_key] = available[header]
                break
    return mapping


def get_panel_metric_schema(tipo_documento, variant=None):
    if tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS:
        return SOCIAL_DIGITAL_METRIC_SCHEMAS.get(variant or 'instagram', SOCIAL_DIGITAL_METRIC_SCHEMAS['instagram'])
    return PANEL_METRIC_SCHEMAS.get(tipo_documento, [])


def get_panel_metric_groups(tipo_documento, variant=None):
    metrics = get_panel_metric_schema(tipo_documento, variant=variant)
    if tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO:
        metric_map = {item['key']: item for item in metrics}
        groups = []
        for category in TRAFFIC_PANEL_CATEGORY_DEFINITIONS:
            groups.append(
                {
                    'key': category['key'],
                    'label': category['label'],
                    'description': category['description'],
                    'metrics': [
                        {
                            **metric_map[key],
                            'tooltip': TRAFFIC_METRIC_TOOLTIPS.get(key, ''),
                        }
                        for key in category['metrics']
                        if key in metric_map
                    ],
                }
            )
        return groups
    if tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.CRM_VENDAS:
        metric_map = {item['key']: item for item in metrics}
        groups = []
        for category in CRM_PANEL_CATEGORY_DEFINITIONS:
            groups.append(
                {
                    'key': category['key'],
                    'label': category['label'],
                    'description': category['description'],
                    'metrics': [
                        {
                            **metric_map[key],
                            'tooltip': CRM_METRIC_TOOLTIPS.get(key, ''),
                        }
                        for key in category['metrics']
                        if key in metric_map
                    ],
                }
            )
        return groups
    if tipo_documento == ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS:
        metric_map = {item['key']: item for item in metrics}
        groups = []
        categories = SOCIAL_DIGITAL_CATEGORY_DEFINITIONS.get(variant or 'instagram', SOCIAL_DIGITAL_CATEGORY_DEFINITIONS['instagram'])
        tooltips = SOCIAL_DIGITAL_METRIC_TOOLTIPS.get(variant or 'instagram', SOCIAL_DIGITAL_METRIC_TOOLTIPS['instagram'])
        for category in categories:
            groups.append(
                {
                    'key': category['key'],
                    'label': category['label'],
                    'description': category['description'],
                    'metrics': [
                        {
                            **metric_map[key],
                            'tooltip': tooltips.get(key, ''),
                        }
                        for key in category['metrics']
                        if key in metric_map
                    ],
                }
            )
        return groups
    return [
        {
            'key': 'geral',
            'label': 'Resumo',
            'description': 'Ative as métricas que deseja exibir no painel.',
            'metrics': [{**item, 'tooltip': ''} for item in metrics],
        }
    ]


def normalize_panel_metric_config(tipo_documento, raw_config, variant=None):
    groups = get_panel_metric_groups(tipo_documento, variant=variant)
    metric_keys = [metric['key'] for group in groups for metric in group['metrics']]
    category_keys = [group['key'] for group in groups]
    if isinstance(raw_config, dict):
        metrics = {}
        for key in metric_keys:
            metric_state = (raw_config.get('metrics') or {}).get(key, {})
            metrics[key] = {
                'table': bool(metric_state.get('table', True)),
                'chart': bool(metric_state.get('chart', True)),
            }
        categories = {}
        raw_categories = raw_config.get('categories') or {}
        filters = {}
        raw_filters = raw_config.get('filters') or {}
        for group in groups:
            group_key = group['key']
            has_any_metric = any(
                metrics[metric['key']]['table'] or metrics[metric['key']]['chart']
                for metric in group['metrics']
            )
            raw_category_enabled = bool(raw_categories.get(group_key, has_any_metric))
            categories[group_key] = raw_category_enabled and has_any_metric
            group_filter_config = raw_filters.get(group_key, {})
            filters[group_key] = {
                'enabled': bool(group_filter_config.get('enabled', False)),
            }
        return {'categories': categories, 'metrics': metrics, 'filters': filters}

    selected_keys = set(raw_config or metric_keys)
    return {
        'categories': {key: True for key in category_keys},
        'filters': {key: {'enabled': False} for key in category_keys},
        'metrics': {
            key: {
                'table': key in selected_keys,
                'chart': key in selected_keys,
            }
            for key in metric_keys
        },
    }




def get_enabled_table_metric_keys(tipo_documento, raw_config, variant=None):
    config = normalize_panel_metric_config(tipo_documento, raw_config, variant=variant)
    enabled = []
    for group in get_panel_metric_groups(tipo_documento, variant=variant):
        if not config['categories'].get(group['key'], True):
            continue
        for metric in group['metrics']:
            if config['metrics'].get(metric['key'], {}).get('table'):
                enabled.append(metric['key'])
    return enabled


def get_enabled_chart_metric_keys(tipo_documento, raw_config, variant=None):
    config = normalize_panel_metric_config(tipo_documento, raw_config, variant=variant)
    enabled = []
    for group in get_panel_metric_groups(tipo_documento, variant=variant):
        if not config['categories'].get(group['key'], True):
            continue
        for metric in group['metrics']:
            if config['metrics'].get(metric['key'], {}).get('chart'):
                enabled.append(metric['key'])
    return enabled


def get_category_filter_enabled_map(tipo_documento, raw_config, variant=None):
    config = normalize_panel_metric_config(tipo_documento, raw_config, variant=variant)
    return {
        group['key']: bool((config.get('filters') or {}).get(group['key'], {}).get('enabled', False))
        for group in get_panel_metric_groups(tipo_documento, variant=variant)
    }


def inspect_uploaded_file(file_obj_or_path, file_name=''):
    dataframe = read_uploaded_dataframe(file_obj_or_path, file_name=file_name)
    preview_rows = dataframe.head(5).to_dict(orient='records')
    sanitized_rows = [{str(key): _serialize_cell(value) for key, value in row.items()} for row in preview_rows]
    source_name = file_name or getattr(file_obj_or_path, 'name', '') or str(file_obj_or_path)
    return UploadPreview(
        columns=list(dataframe.columns),
        rows=sanitized_rows,
        file_name=Path(source_name).name,
    )


def read_uploaded_dataframe(file_obj_or_path, file_name=''):
    source_name = file_name or getattr(file_obj_or_path, 'name', '') or str(file_obj_or_path)
    suffix = Path(source_name).suffix.lower()
    reader = _read_excel if suffix in {'.xlsx', '.xls'} else _read_csv
    dataframe = reader(file_obj_or_path)
    dataframe = dataframe.dropna(how='all')
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    dataframe = dataframe.fillna('')
    return dataframe


def _read_csv(file_obj_or_path):
    errors = []
    for encoding in ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']:
        try:
            source = _resettable_source(file_obj_or_path)
            return pd.read_csv(source, sep=None, engine='python', encoding=encoding)
        except Exception as exc:  # pragma: no cover - defensive I/O fallback
            errors.append(f'{encoding}: {exc}')
    raise ValueError('Falha ao ler o arquivo. Verifique o separador, o encoding e o cabeçalho.')


def _read_excel(file_obj_or_path):
    suffix = Path(getattr(file_obj_or_path, 'name', '') or str(file_obj_or_path)).suffix.lower()
    engine = 'xlrd' if suffix == '.xls' else 'openpyxl'
    if importlib.util.find_spec(engine) is None:
        raise ValueError(f'Leitura de planilhas {suffix or "Excel"} indisponível. Instale a dependência "{engine}".')
    try:
        return pd.read_excel(_resettable_source(file_obj_or_path), engine=engine)
    except Exception as exc:  # pragma: no cover - defensive I/O fallback
        raise ValueError('Falha ao ler a planilha enviada.') from exc


def _serialize_cell(value):
    if hasattr(value, 'isoformat'):
        try:
            return value.isoformat()
        except TypeError:  # pragma: no cover - defensive serialization
            return str(value)
    return str(value)


def _resettable_source(file_obj_or_path):
    if isinstance(file_obj_or_path, (str, Path)):
        return file_obj_or_path
    if hasattr(file_obj_or_path, 'seek'):
        file_obj_or_path.seek(0)
    if hasattr(file_obj_or_path, 'read'):
        content = file_obj_or_path.read()
        if hasattr(file_obj_or_path, 'seek'):
            file_obj_or_path.seek(0)
        return BytesIO(content)
    return file_obj_or_path
