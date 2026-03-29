from django import template
from django.utils.html import format_html


register = template.Library()


@register.filter
def get_item(value, key):
    if isinstance(value, dict):
        return value.get(key, '')
    return ''


@register.filter
def social_icon(network):
    icons = {
        'instagram': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3.5" y="3.5" width="17" height="17" rx="5"></rect><circle cx="12" cy="12" r="4"></circle><circle cx="17.5" cy="6.5" r="1"></circle></svg>',
        'facebook': '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M13.5 21v-7h2.3l.4-3h-2.7V9.2c0-.9.3-1.5 1.6-1.5H16.4V5.1c-.2 0-1-.1-2-.1-2.4 0-4 1.5-4 4.2V11H8v3h2.4v7z"/></svg>',
        'linkedin': '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M6.5 8.5A1.5 1.5 0 1 0 6.5 5a1.5 1.5 0 0 0 0 3.5M5 9.8h3V19H5zm5 0h2.9V11c.4-.7 1.2-1.4 2.4-1.4 1.7 0 2.2 1.1 2.2 2.8V19h3v-7.2c0-3.2-1.8-4.7-4.2-4.7-1.7 0-2.8.9-3.4 1.8V9.8H10z"/></svg>',
        'youtube': '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M21 8.5a2.8 2.8 0 0 0-2-2C17.3 6 12 6 12 6s-5.3 0-7 .5a2.8 2.8 0 0 0-2 2A29 29 0 0 0 3 12a29 29 0 0 0 .5 3.5 2.8 2.8 0 0 0 2 2C6.7 18 12 18 12 18s5.3 0 7-.5a2.8 2.8 0 0 0 2-2A29 29 0 0 0 21 12a29 29 0 0 0-.5-3.5M10 15V9l5 3z"/></svg>',
        'tiktok': '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M14.5 4c.5 1.6 1.5 2.8 3 3.5.6.3 1.3.5 2 .5V11a8 8 0 0 1-5-1.6v5.4a5.3 5.3 0 1 1-4.2-5.2v3a2.3 2.3 0 1 0 1.2 2V4z"/></svg>',
        'x': '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.9 3H21l-6.6 7.5L22 21h-6l-4.7-6.1L5.8 21H3.7l7-8L3 3h6.2l4.2 5.6zm-1 16h1.7L8.3 4.9H6.5z"/></svg>',
        'site': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="12" cy="12" r="9"></circle><path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"></path></svg>',
        'whatsapp': '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 3a9 9 0 0 0-7.8 13.5L3 21l4.7-1.2A9 9 0 1 0 12 3m0 1.8a7.2 7.2 0 0 1 6.1 11l-.3.5.7 2.7-2.8-.7-.4.2a7.2 7.2 0 1 1-3.3-13.7m-2.2 3.8c-.2 0-.5 0-.7.3-.2.2-.8.8-.8 1.9s.8 2.2.9 2.3c.1.2 1.6 2.6 4 3.5 1.9.8 2.4.6 2.8.6.4-.1 1.3-.5 1.5-1 .2-.6.2-1 .1-1 0-.1-.2-.2-.4-.3l-1.4-.7c-.2-.1-.4 0-.5.2l-.6.8c-.1.1-.3.2-.5.1-.2-.1-.9-.3-1.7-1.1-.7-.6-1.1-1.3-1.2-1.5-.1-.2 0-.3.1-.4l.4-.5.2-.3c.1-.1.1-.3 0-.4l-.6-1.5c-.1-.3-.3-.3-.4-.3"/></svg>',
        'outro': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M10 14a5 5 0 0 1 0-7l1.5-1.5a5 5 0 0 1 7 7L17 14"></path><path d="M14 10a5 5 0 0 1 0 7L12.5 18.5a5 5 0 1 1-7-7L7 10"></path></svg>',
    }
    return format_html(icons.get(network, icons['outro']))
