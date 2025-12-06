from jdatetime import datetime as jdatetime


def get_jalali_date_info(gregorian_date):
    """
    Converts a datetime.date object to Jalali date, string, and Iranian weekday name.
    """
    if not gregorian_date:
        return {}

    jalali = jdatetime.fromgregorian(date=gregorian_date)
    # Weekday names starting from Saturday (jdatetime.weekday() gives 0 for Saturday)
    weekday_names = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']

    return {
        'jalali_date': jalali,
        'jalali_str': jalali.strftime('%Y/%m/%d'),
        'weekday': weekday_names[jalali.weekday()]
    }
