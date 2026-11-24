from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def yen(value):
    """金額を「1,234,567円」の形式にする。

    Django の日本語ロケールは NUMBER_GROUPING = 0（桁区切りなし）のため、
    floatformat:"0g" や intcomma では桁区切りが付かない。そこで自前で整形する。
    """
    try:
        number = int(Decimal(value))
    except (InvalidOperation, TypeError, ValueError):
        return ''
    return f'{number:,}円'
