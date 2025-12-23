from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Tuple

import jdatetime
from django.db.models import QuerySet

JALALI_MONTHS_FA = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def jalali_month_choices() -> List[dict]:
    """
    For template dropdown:
    [{'value': 1, 'label': 'فروردین'}, ...]
    """
    return [{"value": i + 1, "label": name} for i, name in enumerate(JALALI_MONTHS_FA)]


def _gregorian_range_from_jalali_year_month(jy: int, jm: int) -> Tuple[datetime, datetime]:
    """
    [start, end) range in Gregorian datetimes for a Jalali (year, month).
    Works with USE_TZ = False (naive datetimes).
    """
    start_j = jdatetime.date(jy, jm, 1)

    if jm == 12:
        next_j = jdatetime.date(jy + 1, 1, 1)
    else:
        next_j = jdatetime.date(jy, jm + 1, 1)

    start_g = start_j.togregorian()
    end_g = next_j.togregorian()

    start_dt = datetime(start_g.year, start_g.month, start_g.day, 0, 0, 0)
    end_dt = datetime(end_g.year, end_g.month, end_g.day, 0, 0, 0)
    return start_dt, end_dt


def gregorian_range_from_jalali_year(jy: int) -> Tuple[datetime, datetime]:
    """
    [start, end) range in Gregorian for a Jalali year.
    """
    start_dt, _ = _gregorian_range_from_jalali_year_month(jy, 1)
    end_dt, _ = _gregorian_range_from_jalali_year_month(jy + 1, 1)
    return start_dt, end_dt


def gregorian_range_from_jalali_year_month(jy: int, jm: int) -> Tuple[datetime, datetime]:
    """
    [start, end) range in Gregorian for a Jalali year-month.
    """
    return _gregorian_range_from_jalali_year_month(jy, jm)


def filter_qs_by_jalali_year(qs: QuerySet, jy: int, field: str = "published_at") -> QuerySet:
    start_dt, end_dt = gregorian_range_from_jalali_year(jy)
    return qs.filter(**{f"{field}__gte": start_dt, f"{field}__lt": end_dt})


def filter_qs_by_jalali_month(qs: QuerySet, jy: int, jm: int, field: str = "published_at") -> QuerySet:
    start_dt, end_dt = gregorian_range_from_jalali_year_month(jy, jm)
    return qs.filter(**{f"{field}__gte": start_dt, f"{field}__lt": end_dt})


def jalali_year_choices_from_min_max(min_dt, max_dt):
    """
    min_dt/max_dt: datetime
    output: [1401, 1402, 1403, ...] desc
    """
    if not min_dt or not max_dt:
        return []

    min_jy = jdatetime.datetime.fromgregorian(datetime=min_dt).year
    max_jy = jdatetime.datetime.fromgregorian(datetime=max_dt).year
    return list(range(max_jy, min_jy - 1, -1))
