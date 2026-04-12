from __future__ import annotations

from django.template.loader import render_to_string


def render_report_html(context):
    return render_to_string('relatorios/report_export.html', context)
