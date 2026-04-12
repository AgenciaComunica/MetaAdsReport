import calendar
from datetime import date, timedelta

_MESES_PT = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro',
}


def _mes_label(d):
    return f'{_MESES_PT[d.month]} {d.year}'


def available_months(earliest_date=None):
    """Retorna lista de dicts {value, label} do mês atual até o mais antigo, ordem decrescente."""
    today = date.today()
    end = date(today.year, today.month, 1)
    if earliest_date:
        start = date(earliest_date.year, earliest_date.month, 1)
    else:
        # Padrão: 18 meses atrás
        y, m = today.year, today.month - 17
        while m <= 0:
            m += 12
            y -= 1
        start = date(y, m, 1)

    months = []
    cursor = end
    while cursor >= start:
        months.append({
            'value': cursor.strftime('%Y-%m'),
            'label': _mes_label(cursor),
        })
        prev = cursor - timedelta(days=1)
        cursor = date(prev.year, prev.month, 1)
    return months


def month_ranges_for_param(mes_param):
    """Recebe 'YYYY-MM' e retorna datas de início/fim do mês e do anterior."""
    try:
        year, month = int(mes_param[:4]), int(mes_param[5:7])
        _, last_day = calendar.monthrange(year, month)
        current_start = date(year, month, 1)
        current_end = date(year, month, last_day)
    except (ValueError, IndexError, TypeError):
        return last_complete_month_ranges()
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    return {
        'current_start': current_start,
        'current_end': current_end,
        'previous_start': previous_start,
        'previous_end': previous_end,
    }


def last_complete_month_ranges(reference_date=None):
    reference_date = reference_date or date.today()

    current_month_start = reference_date.replace(day=1)
    current_period_end = current_month_start - timedelta(days=1)
    current_period_start = current_period_end.replace(day=1)

    previous_period_end = current_period_start - timedelta(days=1)
    previous_period_start = previous_period_end.replace(day=1)

    return {
        'current_start': current_period_start,
        'current_end': current_period_end,
        'previous_start': previous_period_start,
        'previous_end': previous_period_end,
    }


def resolve_period_dates(periodo_tipo, data_inicio, data_fim):
    if data_inicio and data_fim:
        return data_inicio, data_fim
    if not data_fim:
        return data_inicio, data_fim
    if periodo_tipo == 'semanal':
        return data_fim - timedelta(days=6), data_fim
    if periodo_tipo == 'mensal':
        return data_fim - timedelta(days=29), data_fim
    if periodo_tipo == 'anual':
        return data_fim - timedelta(days=364), data_fim
    return data_inicio, data_fim
