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
        {'key': 'canal', 'label': 'Canal', 'required': False},
        {'key': 'valor_venda', 'label': 'Valor da Venda', 'required': False},
        {'key': 'vendedor', 'label': 'Vendedor', 'required': False},
        {'key': 'tag_lead', 'label': 'Tag Lead', 'required': False},
        {'key': 'status_fechamento', 'label': 'Status Fechamento', 'required': False},
        {'key': 'origem_lead', 'label': 'Origem do Lead', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS: [
        {'key': 'evento', 'label': 'Evento', 'required': True},
        {'key': 'local_evento', 'label': 'Local do Evento', 'required': False},
        {'key': 'data_evento', 'label': 'Data do Evento', 'required': True},
        {'key': 'nome_lead', 'label': 'Nome do Lead', 'required': True},
        {'key': 'instagram', 'label': 'Instagram', 'required': False},
        {'key': 'telefone_contato', 'label': 'Telefone de Contato', 'required': False},
        {'key': 'idade', 'label': 'Idade', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS: [
        {'key': 'rede_social', 'label': 'Rede Social', 'required': True},
        {'key': 'perfil', 'label': 'Perfil', 'required': True},
        {'key': 'url_perfil', 'label': 'URL do Perfil', 'required': False},
        {'key': 'data_referencia', 'label': 'Data de Referência', 'required': False},
        {'key': 'seguidores', 'label': 'Seguidores', 'required': False},
        {'key': 'publicacoes', 'label': 'Publicações', 'required': False},
        {'key': 'alcance', 'label': 'Alcance', 'required': False},
        {'key': 'impressoes', 'label': 'Impressões', 'required': False},
        {'key': 'engajamento', 'label': 'Engajamento', 'required': False},
    ],
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
        {'key': 'registros', 'label': 'Registros'},
        {'key': 'vendas_fechadas', 'label': 'Vendas Fechadas'},
        {'key': 'receita_total', 'label': 'Receita Total'},
        {'key': 'ticket_medio', 'label': 'Ticket Médio'},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.LEADS_EVENTOS: [
        {'key': 'leads_total', 'label': 'Total de Leads'},
        {'key': 'eventos_total', 'label': 'Eventos'},
        {'key': 'idade_media', 'label': 'Idade Média'},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.REDES_SOCIAIS: [
        {'key': 'perfis_total', 'label': 'Perfis'},
        {'key': 'seguidores_total', 'label': 'Seguidores'},
        {'key': 'publicacoes_total', 'label': 'Publicações'},
        {'key': 'engajamento_total', 'label': 'Engajamento'},
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


@dataclass
class UploadPreview:
    columns: list[str]
    rows: list[dict]
    file_name: str


def get_field_schema(tipo_documento):
    if tipo_documento in UPLOAD_FIELD_SCHEMAS:
        return UPLOAD_FIELD_SCHEMAS[tipo_documento]
    return LEGACY_FIELD_SCHEMAS.get(tipo_documento, [])


def get_type_label(tipo_documento):
    return dict(UPLOAD_TYPE_CHOICES).get(tipo_documento, tipo_documento)


def get_panel_metric_schema(tipo_documento):
    return PANEL_METRIC_SCHEMAS.get(tipo_documento, [])


def get_panel_metric_groups(tipo_documento):
    metrics = get_panel_metric_schema(tipo_documento)
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
    return [
        {
            'key': 'geral',
            'label': 'Resumo',
            'description': 'Ative as métricas que deseja exibir no painel.',
            'metrics': [{**item, 'tooltip': ''} for item in metrics],
        }
    ]


def normalize_panel_metric_config(tipo_documento, raw_config):
    groups = get_panel_metric_groups(tipo_documento)
    metric_keys = [metric['key'] for group in groups for metric in group['metrics']]
    category_keys = [group['key'] for group in groups]
    if isinstance(raw_config, dict):
        categories = {
            key: bool((raw_config.get('categories') or {}).get(key, True))
            for key in category_keys
        }
        metrics = {}
        for key in metric_keys:
            metric_state = (raw_config.get('metrics') or {}).get(key, {})
            metrics[key] = {
                'table': bool(metric_state.get('table', True)),
                'chart': bool(metric_state.get('chart', True)),
            }
        return {'categories': categories, 'metrics': metrics}

    selected_keys = set(raw_config or metric_keys)
    return {
        'categories': {key: True for key in category_keys},
        'metrics': {
            key: {
                'table': key in selected_keys,
                'chart': key in selected_keys,
            }
            for key in metric_keys
        },
    }


def get_enabled_table_metric_keys(tipo_documento, raw_config):
    config = normalize_panel_metric_config(tipo_documento, raw_config)
    enabled = []
    for group in get_panel_metric_groups(tipo_documento):
        if not config['categories'].get(group['key'], True):
            continue
        for metric in group['metrics']:
            if config['metrics'].get(metric['key'], {}).get('table'):
                enabled.append(metric['key'])
    return enabled


def get_enabled_chart_metric_keys(tipo_documento, raw_config):
    config = normalize_panel_metric_config(tipo_documento, raw_config)
    enabled = []
    for group in get_panel_metric_groups(tipo_documento):
        if not config['categories'].get(group['key'], True):
            continue
        for metric in group['metrics']:
            if config['metrics'].get(metric['key'], {}).get('chart'):
                enabled.append(metric['key'])
    return enabled


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
