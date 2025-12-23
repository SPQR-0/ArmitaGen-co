import jdatetime

from django import template
from django.utils.dateparse import parse_datetime, parse_date

register = template.Library()


@register.filter(name="jalali")
def jalali(value, fmt="%Y/%m/%d"):
    """
    Usage:
        {{ post.published_at|jalali }}
        {{ post.published_at|jalali:"%Y/%m/%d - %H:%M" }}
    """
    if not value:
        return ""

    dt = value

    if isinstance(value, str):
        dt = parse_datetime(value) or parse_date(value)
        if not dt:
            return value

    if hasattr(dt, "year") and not hasattr(dt, "hour"):
        return jdatetime.date.fromgregorian(date=dt).strftime(fmt)

    return jdatetime.datetime.fromgregorian(datetime=dt).strftime(fmt)
