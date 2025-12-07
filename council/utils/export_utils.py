import csv
from datetime import datetime

import jdatetime
from django.http import HttpResponse


def export_to_csv(queryset, model_name, fields=None):
    """
    Export queryset to CSV with Jalali dates

    Args:
        queryset: Django queryset to export
        model_name: Name for the CSV file
        fields: List of field names to include (None = all fields)
    """

    # Create response
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    filename = f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Add BOM for Excel UTF-8 compatibility
    response.write('\ufeff')

    writer = csv.writer(response)

    # Get model fields
    if not fields and queryset.exists():
        model = queryset.model
        fields = [f.name for f in model._meta.fields]

    # Write header with Persian names
    headers = []
    for field_name in fields:
        try:
            field = queryset.model._meta.get_field(field_name)
            headers.append(field.verbose_name or field_name)
        except:
            headers.append(field_name)

    writer.writerow(headers)

    # Write data
    for obj in queryset:
        row = []
        for field_name in fields:
            try:
                value = getattr(obj, field_name)

                # Convert datetime to Jalali
                if isinstance(value, datetime):
                    jalali = jdatetime.datetime.fromgregorian(datetime=value)
                    value = jalali.strftime('%Y/%m/%d - %H:%M:%S')

                # Handle ForeignKey
                elif hasattr(value, 'pk'):
                    value = str(value)

                # Handle None
                elif value is None:
                    value = ''

                row.append(value)
            except AttributeError:
                row.append('')

        writer.writerow(row)

    return response


def get_export_fields(model_class):
    """Get available fields for export with their Persian names"""
    fields = []
    for field in model_class._meta.fields:
        fields.append({
            'name': field.name,
            'verbose_name': field.verbose_name or field.name,
            'type': field.get_internal_type()
        })
    return fields
