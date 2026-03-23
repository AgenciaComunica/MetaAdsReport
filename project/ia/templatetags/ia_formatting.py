import re

from django import template
from django.utils.html import conditional_escape, format_html, format_html_join
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter
def render_analysis_markdown(value):
    if not value:
        return ''

    lines = []
    for raw_line in str(value).splitlines():
        line = conditional_escape(raw_line.strip())
        if not line:
            lines.append(mark_safe('<br>'))
            continue

        heading_match = re.match(r'^###\s*(.+)$', line)
        if heading_match:
            lines.append(mark_safe(f'<strong>{heading_match.group(1)}</strong>'))
            continue

        enumerated_match = re.match(r'^(\d+\))\s+\*\*(.+?)\*\*:?\s*(.*)$', line)
        if enumerated_match:
            prefix, title, rest = enumerated_match.groups()
            if rest:
                lines.append(format_html('<strong>{} {}</strong>: {}', prefix, title, mark_safe(rest)))
            else:
                lines.append(format_html('<strong>{} {}</strong>', prefix, title))
            continue

        line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        lines.append(mark_safe(line))

    return format_html_join(mark_safe('<br>'), '{}', ((line,) for line in lines))
