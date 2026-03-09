from datetime import date, timedelta


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
