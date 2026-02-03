from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def rupiah(value):
    """Format number with dot thousand separators for Rupiah."""
    if value is None or value == "":
        return "0"
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    formatted = f"{number:,.0f}"
    return formatted.replace(",", ".")


@register.filter
def comma_number(value):
    """Format number with comma thousand separators."""
    if value is None or value == "":
        return "0"
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return str(value)

    return f"{number:,.0f}"
