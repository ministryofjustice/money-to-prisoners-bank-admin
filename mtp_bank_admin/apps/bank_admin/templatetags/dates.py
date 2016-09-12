from datetime import timedelta
from itertools import count, islice

from django import template
from django.utils.timezone import now

from bank_admin.utils import WorkdayChecker

register = template.Library()


@register.assignment_tag
def get_preceding_workdays(number_of_days, offset=0):
    """
    Returns a list of weekdays counting backwards from today
    :param number_of_days: number of weekdays to include in total
    :param offset: number of days ago to start from; if 0 today is included
    """

    def day_generator():
        current = now().date()
        for day in count():
            yield current - timedelta(days=day)
    days = day_generator()
    checker = WorkdayChecker()
    days = filter(checker.is_workday, days)
    days = islice(days, offset, number_of_days + offset)

    return list(days)
