from datetime import timedelta

from django import template
from django.utils.timezone import now

register = template.Library()


@register.assignment_tag
def get_preceding_days(number_of_days, offset=0):
    current = now().date()
    days = [current - timedelta(days=day) for day in range(offset, offset + number_of_days)]
    return days
