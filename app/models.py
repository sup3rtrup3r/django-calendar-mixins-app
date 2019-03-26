import datetime
from django.db import models
from django.utils import timezone


class Schedule(models.Model):
    """Raspored"""
    summary = models.CharField('Overview', max_length=50)
    description = models.TextField('Detailed description', blank=True)
    start_time = models.TimeField('Start time', default=datetime.time(7, 0, 0))
    end_time = models.TimeField('End time', default=datetime.time(7, 0, 0))
    date = models.DateField('Date')
    created_at = models.DateTimeField('Created date', default=timezone.now)

    def __str__(self):
        return self.summary
