import jdatetime
from django.utils import timezone


def group_slots_by_jalali_date(slots):
    """
    Groups available time slots by Jalali date for the UI slider.
    Returns a list of dictionaries.
    """
    grouped = {}

    for slot in slots:
        # Convert Gregorian date to Jalali
        j_date = jdatetime.date.fromgregorian(date=slot.date)
        date_str = j_date.strftime("%Y/%m/%d")

        if date_str not in grouped:
            grouped[date_str] = {
                'date_obj': j_date,
                'day_name': j_date.strftime("%A"),  # Shanbe, Yekshanbe...
                'date_formatted': j_date.strftime("%d %B"),  # 12 Azar
                'full_date': date_str,
                'slots': []
            }

        grouped[date_str]['slots'].append(slot)

    # Sort by date and return list
    return sorted(grouped.values(), key=lambda x: x['full_date'])