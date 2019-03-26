import calendar
from collections import deque
import datetime
import itertools
from django import forms


class BaseCalendarMixin:
    """Base class for Calendar related Mixin"""
    first_weekday = 0  # 0 is Monday and 1 is Tuesday. 6 is from Sunday. If you wish, please specify in the inherited view.
    week_names = ['pon', 'uto', 'sri', 'čet', 'pet', 'sub', 'ned']  # This assumes to write from Monday. ['Mon', 'Tue' ...

    def setup(self):
        """Internal calendar setting process

        Instantiate to use the functionality of the calendar.Calendar class.
        We use monthdatescalendar method of Calendar class, but default is from Monday
        This is a setup process to handle the case where you want to display from Tuesday (first_weekday = 1).

        """
        self._calendar = calendar.Calendar(self.first_weekday)

    def get_week_names(self):
        """Shift week_names to first_weekday (the first day of the week)"""
        week_names = deque(self.week_names)
        week_names.rotate(-self.first_weekday)  # Move elements in the list one by one to the right ... When you use deque, it is interesting
        return week_names


class MonthCalendarMixin(BaseCalendarMixin):
    """Mixin provides monthly calendar function"""

    def get_previous_month(self, date):
        """Return the previous month"""
        if date.month == 1:
            return date.replace(year=date.year-1, month=12, day=1)
        else:
            return date.replace(month=date.month-1, day=1)

    def get_next_month(self, date):
        """Return next month"""
        if date.month == 12:
            return date.replace(year=date.year+1, month=1, day=1)
        else:
            return date.replace(month=date.month+1, day=1)

    def get_month_days(self, date):
        """Return all days of the month"""
        return self._calendar.monthdatescalendar(date.year, date.month)

    def get_current_month(self):
        """Return the current month"""
        month = self.kwargs.get('month')
        year = self.kwargs.get('year')
        if month and year:
            month = datetime.date(year=int(year), month=int(month), day=1)
        else:
            month = datetime.date.today().replace(day=1)
        return month

    def get_month_calendar(self):
        """Return a dictionary with monthly calendar information"""
        self.setup()
        current_month = self.get_current_month()
        calendar_data = {
            'now': datetime.date.today(),
            'month_days': self.get_month_days(current_month),
            'month_current': current_month,
            'month_previous': self.get_previous_month(current_month),
            'month_next': self.get_next_month(current_month),
            'week_names': self.get_week_names(),
        }
        return calendar_data


class WeekCalendarMixin(BaseCalendarMixin):
    """Mixin provides weekly calendar functionality"""

    def get_week_days(self):
        """Return all days of the week"""
        month = self.kwargs.get('month')
        year = self.kwargs.get('year')
        day = self.kwargs.get('day')
        if month and year and day:
            date = datetime.date(year=int(year), month=int(month), day=int(day))
        else:
            date = datetime.date.today()

        for week in self._calendar.monthdatescalendar(date.year, date.month):
            if date in week:  # Retrieved weekly, all content is datetime.date type. If the relevant day is included, it is the week that should be displayed this time
                return week

    def get_week_calendar(self):
        """Return a dictionary with weekly calendar information"""
        self.setup()
        days = self.get_week_days()
        first = days[0]
        last = days[-1]
        calendar_data = {
            'now': datetime.date.today(),
            'week_days': days,
            'week_previous': first - datetime.timedelta(days=7),
            'week_next': first + datetime.timedelta(days=7),
            'week_names': self.get_week_names(),
            'week_first': first,
            'week_last': last,
        }
        return calendar_data


class WeekWithScheduleMixin(WeekCalendarMixin):
    """Mixin provides a scheduled, weekly calendar"""

    def get_week_schedules(self, start, end, days):
        """Return each day and schedule"""
        lookup = {
            # Dynamically create 'for example, date__range:
            '{}__range'.format(self.date_field): (start, end)
        }
        # For example, Schedule.objects.filter (date__range = (1st, 31st))
        queryset = self.model.objects.filter(**lookup)

        # Create a dictionary like {1 day datetime: all day schedules, 2 day datetime: all 2 days ...}
        day_schedules = {day: [] for day in days}
        for schedule in queryset:
            schedule_date = getattr(schedule, self.date_field)
            day_schedules[schedule_date].append(schedule)
        return day_schedules

    def get_week_calendar(self):
        calendar_context = super().get_week_calendar()
        calendar_context['week_day_schedules'] = self.get_week_schedules(
            calendar_context['week_first'],
            calendar_context['week_last'],
            calendar_context['week_days']
        )
        return calendar_context


class MonthWithScheduleMixin(MonthCalendarMixin):
    """Mixin offers a monthly calendar with a schedule"""

    def get_month_schedules(self, start, end, days):
        """Return each day and schedule"""
        lookup = {
            # Dynamically create 'for example, date__range:
            '{}__range'.format(self.date_field): (start, end)
        }
        # For example, Schedule.objects.filter (date__range = (1st, 31st))
        queryset = self.model.objects.filter(**lookup)

        # Create a dictionary like {1 day datetime: all day schedules, 2 day datetime: all 2 days ...}
        day_schedules = {day: [] for week in days for day in week}
        for schedule in queryset:
            schedule_date = getattr(schedule, self.date_field)
            day_schedules[schedule_date].append(schedule)

        # Divide the day_schedules dictionary into each week. [{1 day: 1 day schedule ...}, {8 days: 8 day schedule ...}, ...]
        # 7 pieces are taken out and divided.
        size = len(day_schedules)
        return [{key: day_schedules[key] for key in itertools.islice(day_schedules, i, i+7)} for i in range(0, size, 7)]

    def get_month_calendar(self):
        calendar_context = super().get_month_calendar()
        month_days = calendar_context['month_days']
        month_first = month_days[0][0]
        month_last = month_days[-1][-1]
        calendar_context['month_day_schedules'] = self.get_month_schedules(
            month_first,
            month_last,
            month_days
        )
        return calendar_context


class MonthWithFormsMixin(MonthCalendarMixin):
    """Mixin offers a monthly calendar with a schedule"""

    def get_month_forms(self, start, end, days):
        """Create a form linked to each day"""
        lookup = {
            # Dynamically create 'for example, date__range:
            '{}__range'.format(self.date_field): (start, end)
        }
        # For example, Schedule.objects.filter (date__range = (1st, 31st))
        queryset = self.model.objects.filter(**lookup)
        days_count = sum(len(week) for week in days)
        FormClass = forms.modelformset_factory(self.model, self.form_class, extra=days_count)
        if self.request.method == 'POST':
            formset = self.month_formset = FormClass(self.request.POST, queryset=queryset)
        else:
            formset = self.month_formset = FormClass(queryset=queryset)

        # Create a dictionary like {1 day datetime: 1 day related forms, 2 day datetime: 2 day forms ...}
        day_forms = {day: [] for week in days for day in week}

        # Place one new creation form each day
        for empty_form, (date, empty_list) in zip(formset.extra_forms, day_forms.items()):
            empty_form.initial = {self.date_field: date}
            empty_list.append(empty_form)

        # Place a form for updating the schedule each day there is a schedule
        for bound_form in formset.initial_forms:
            instance = bound_form.instance
            date = getattr(instance, self.date_field)
            day_forms[date].append(bound_form)

        # The day_forms dictionary is divided on a lap basis. [{1st: 1st form ...}, {8th: 8th form ...}, ...]
        # 7 pieces are taken out and divided.
        return [{key: day_forms[key] for key in itertools.islice(day_forms, i, i+7)} for i in range(0, days_count, 7)]

    def get_month_calendar(self):
        calendar_context = super().get_month_calendar()
        month_days = calendar_context['month_days']
        month_first = month_days[0][0]
        month_last = month_days[-1][-1]
        calendar_context['month_day_forms'] = self.get_month_forms(
            month_first,
            month_last,
            month_days
        )
        calendar_context['month_formset'] = self.month_formset
        return calendar_context
