from django import template

from bank_admin.utils import get_preceding_workday_list

register = template.Library()


@register.assignment_tag
def get_preceding_workdays(number_of_days, offset=0):
    """
    Returns a list of weekdays counting backwards from today
    :param number_of_days: number of weekdays to include in total
    :param offset: number of days ago to start from; if 0 today is included
    """

    return get_preceding_workday_list(number_of_days, offset)
