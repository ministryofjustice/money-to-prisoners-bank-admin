import datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from django import template

register = template.Library()


@register.filter
def currency(pence_value):
    try:
        return '£{:,.2f}'.format(pence_value / 100)
    except TypeError:
        return pence_value


@register.filter
def parse_date_field(date_str):
    parsers = [parse_datetime, parse_date]
    for parser in parsers:
        try:
            parsed_value = parser(date_str)
            if not parsed_value:
                continue
            if isinstance(parsed_value, datetime.datetime):
                parsed_value = timezone.localtime(parsed_value)
            return parsed_value.date()
        except (ValueError, TypeError):
            pass
    return date_str
