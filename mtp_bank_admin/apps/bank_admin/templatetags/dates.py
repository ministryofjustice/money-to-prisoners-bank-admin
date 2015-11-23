from datetime import date, timedelta

from django import template

register = template.Library()


@register.assignment_tag
def get_preceding_days(number_of_days, offset=0, format_string='%Y-%m-%d'):
    days = []
    current = date.today() - timedelta(days=offset)
    for _ in range(number_of_days):
        days.append(current.strftime(format_string))
        current = current - timedelta(days=1)
    return days
