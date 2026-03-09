from __future__ import annotations

from io import BytesIO

from django.template.loader import render_to_string

try:  # pragma: no cover - optional dependency
    from weasyprint import HTML
except Exception:  # pragma: no cover
    HTML = None


def render_report_html(context):
    return render_to_string('relatorios/report_export.html', context)


def render_pdf_bytes(html_string, base_url=None):
    if HTML is None:
        return None
    pdf_buffer = BytesIO()
    HTML(string=html_string, base_url=base_url).write_pdf(pdf_buffer)
    return pdf_buffer.getvalue()
