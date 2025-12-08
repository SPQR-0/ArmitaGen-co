from django.contrib.admin import SimpleListFilter
from django import forms
from django.utils.translation import gettext_lazy as _
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget


class JalaliDateRangeForm(forms.Form):
    start_date = JalaliDateField(
        required=False,
        widget=AdminJalaliDateWidget(attrs={'placeholder': 'از تاریخ'})
    )
    end_date = JalaliDateField(
        required=False,
        widget=AdminJalaliDateWidget(attrs={'placeholder': 'تا تاریخ'})
    )


class JalaliDateRangeFilter(SimpleListFilter):
    title = _('بازه تاریخ')
    parameter_name = 'dummy'   # مهم نیست، فقط باید چیزی باشد
    template = 'admin/jalali_date_range_filter.html'

    date_field = 'date'

    def lookups(self, request, model_admin):
        return ()

    def choices(self, changelist):
        form = JalaliDateRangeForm(changelist.params)
        yield {
            'form': form,
            'params': changelist.params,
            'query_string': changelist.get_query_string,
        }

    def queryset(self, request, queryset):
        form = JalaliDateRangeForm(request.GET)

        if form.is_valid():
            start = form.cleaned_data.get('start_date')
            end = form.cleaned_data.get('end_date')

            field = self.date_field

            if start:
                queryset = queryset.filter(**{f'{field}__gte': start.to_gregorian()})
            if end:
                queryset = queryset.filter(**{f'{field}__lte': end.to_gregorian()})

        return queryset
