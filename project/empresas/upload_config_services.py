from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pandas as pd

from .models import ConfiguracaoUploadEmpresa


UPLOAD_FIELD_SCHEMAS = {
    ConfiguracaoUploadEmpresa.TipoDocumento.TRAFEGO_PAGO: [
        {'key': 'data', 'label': 'Data', 'required': True},
        {'key': 'campanha', 'label': 'Campanha', 'required': True},
        {'key': 'conjunto', 'label': 'Conjunto', 'required': False},
        {'key': 'anuncio', 'label': 'Anúncio', 'required': False},
        {'key': 'origem', 'label': 'Origem', 'required': False},
        {'key': 'investimento', 'label': 'Investimento', 'required': False},
        {'key': 'impressoes', 'label': 'Impressões', 'required': False},
        {'key': 'cliques', 'label': 'Cliques', 'required': False},
        {'key': 'resultados', 'label': 'Resultados', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.EVENTOS: [
        {'key': 'evento', 'label': 'Evento', 'required': True},
        {'key': 'data_evento', 'label': 'Data do Evento', 'required': True},
        {'key': 'origem', 'label': 'Origem', 'required': False},
        {'key': 'canal', 'label': 'Canal', 'required': False},
        {'key': 'responsavel', 'label': 'Responsável', 'required': False},
        {'key': 'status', 'label': 'Status', 'required': False},
        {'key': 'valor', 'label': 'Valor', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.VENDAS: [
        {'key': 'pedido_id', 'label': 'Pedido / ID', 'required': True},
        {'key': 'data_venda', 'label': 'Data da Venda', 'required': True},
        {'key': 'cliente', 'label': 'Cliente', 'required': False},
        {'key': 'produto', 'label': 'Produto', 'required': False},
        {'key': 'quantidade', 'label': 'Quantidade', 'required': False},
        {'key': 'valor_total', 'label': 'Valor Total', 'required': True},
        {'key': 'canal', 'label': 'Canal', 'required': False},
        {'key': 'status', 'label': 'Status', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.LEADS: [
        {'key': 'lead_id', 'label': 'Lead / ID', 'required': True},
        {'key': 'data_captura', 'label': 'Data de Captura', 'required': True},
        {'key': 'nome_contato', 'label': 'Nome', 'required': False},
        {'key': 'email', 'label': 'E-mail', 'required': False},
        {'key': 'telefone', 'label': 'Telefone', 'required': False},
        {'key': 'origem', 'label': 'Origem', 'required': False},
        {'key': 'campanha', 'label': 'Campanha', 'required': False},
        {'key': 'status', 'label': 'Status', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.CRM: [
        {'key': 'contato_id', 'label': 'Contato / ID', 'required': True},
        {'key': 'nome_contato', 'label': 'Nome do Contato', 'required': False},
        {'key': 'origem', 'label': 'Origem', 'required': False},
        {'key': 'etapa_funil', 'label': 'Etapa do Funil', 'required': True},
        {'key': 'responsavel', 'label': 'Responsável', 'required': False},
        {'key': 'ultima_interacao', 'label': 'Última Interação', 'required': False},
        {'key': 'valor_oportunidade', 'label': 'Valor da Oportunidade', 'required': False},
        {'key': 'status', 'label': 'Status', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.FINANCEIRO: [
        {'key': 'lancamento_id', 'label': 'Lançamento / ID', 'required': True},
        {'key': 'data_competencia', 'label': 'Data de Competência', 'required': True},
        {'key': 'categoria', 'label': 'Categoria', 'required': True},
        {'key': 'descricao', 'label': 'Descrição', 'required': False},
        {'key': 'centro_custo', 'label': 'Centro de Custo', 'required': False},
        {'key': 'valor', 'label': 'Valor', 'required': True},
        {'key': 'status', 'label': 'Status', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.ESTOQUE: [
        {'key': 'sku', 'label': 'SKU', 'required': True},
        {'key': 'produto', 'label': 'Produto', 'required': True},
        {'key': 'categoria', 'label': 'Categoria', 'required': False},
        {'key': 'quantidade', 'label': 'Quantidade', 'required': True},
        {'key': 'local', 'label': 'Local', 'required': False},
        {'key': 'custo_unitario', 'label': 'Custo Unitário', 'required': False},
        {'key': 'atualizado_em', 'label': 'Atualizado em', 'required': False},
    ],
    ConfiguracaoUploadEmpresa.TipoDocumento.ATENDIMENTO: [
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


@dataclass
class UploadPreview:
    columns: list[str]
    rows: list[dict]
    file_name: str


def get_field_schema(tipo_documento):
    return UPLOAD_FIELD_SCHEMAS.get(tipo_documento, [])


def get_type_label(tipo_documento):
    return dict(UPLOAD_TYPE_CHOICES).get(tipo_documento, tipo_documento)


def build_upload_slots(empresa):
    configuracoes = {
        config.tipo_documento: config
        for config in empresa.configuracoes_upload.all()
    }
    slots = []
    for tipo, label in UPLOAD_TYPE_CHOICES:
        slots.append(
            {
                'tipo': tipo,
                'label': label,
                'configuracao': configuracoes.get(tipo),
            }
        )
    return slots


def inspect_uploaded_file(file_obj_or_path, file_name=''):
    source_name = file_name or getattr(file_obj_or_path, 'name', '') or str(file_obj_or_path)
    suffix = Path(source_name).suffix.lower()
    reader = _read_excel if suffix in {'.xlsx', '.xls'} else _read_csv
    dataframe = reader(file_obj_or_path)
    dataframe = dataframe.dropna(how='all')
    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    dataframe = dataframe.fillna('')
    preview_rows = dataframe.head(5).to_dict(orient='records')
    sanitized_rows = [{str(key): _serialize_cell(value) for key, value in row.items()} for row in preview_rows]
    return UploadPreview(
        columns=list(dataframe.columns),
        rows=sanitized_rows,
        file_name=Path(source_name).name,
    )


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
    try:
        return pd.read_excel(_resettable_source(file_obj_or_path))
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
