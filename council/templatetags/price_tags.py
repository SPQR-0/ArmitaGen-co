from django import template

register = template.Library()


@register.filter(name='toman')
def toman(value):
    """
    Format price with thousand separators for Toman
    Example: 1250000 -> 1,250,000
    """
    try:
        value = int(value)
        return f"{value:,}"
    except (ValueError, TypeError):
        return value
