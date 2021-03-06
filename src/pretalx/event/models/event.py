import pytz
from django.conf import settings
from django.core.mail import get_connection
from django.core.mail.backends.base import BaseEmailBackend
from django.core.validators import RegexValidator
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from i18nfield.fields import I18nCharField

from pretalx.common.mixins import LogMixin
from pretalx.common.models.settings import settings_hierarkey


@settings_hierarkey.add()
class Event(LogMixin, models.Model):
    name = I18nCharField(
        max_length=200,
        verbose_name=_('Name'),
    )
    slug = models.SlugField(
        max_length=50, db_index=True,
        help_text=_('Should be short, only contain lowercase letters and numbers, and must be unique.'),
        validators=[
            RegexValidator(
                regex="^[a-zA-Z0-9.-]+$",
                message=_('The slug may only contain letters, numbers, dots and dashes.'),
            ),
        ],
        verbose_name=_("Short form"),
    )
    subtitle = I18nCharField(
        max_length=200,
        verbose_name=_('Subitle'),
        null=True, blank=True,
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name=_('Event is public')
    )
    permitted = models.ManyToManyField(
        to='person.User',
        through='person.EventPermission',
        related_name="events",
    )
    date_from = models.DateField(
        null=True, blank=True,
        verbose_name=_('Event start date'),
    )
    date_to = models.DateField(
        null=True, blank=True,
        verbose_name=_('Event end date'),
    )
    timezone = models.CharField(
        choices=[(tz, tz) for tz in pytz.common_timezones],
        max_length=30,
        default='UTC',
    )
    email = models.EmailField(
        verbose_name=_('Orga email address'),
        help_text=_('Will be used as sender/reply-to in emails'),
        null=True, blank=True,
    )
    color = models.CharField(
        max_length=7,
        verbose_name=_('Main event color'),
        help_text=_('Please provide a hex value like #00ff00 if you do not like pretalx colors.'),
        null=True, blank=True,
        validators=[],
    )
    locale_array = models.TextField(default=settings.LANGUAGE_CODE)
    locale = models.CharField(max_length=32, default=settings.LANGUAGE_CODE,
                              choices=settings.LANGUAGES,
                              verbose_name=_('Default language'))
    accept_template = models.ForeignKey(
        to='mail.MailTemplate', on_delete=models.CASCADE,
        related_name='+', null=True, blank=True,
    )
    ack_template = models.ForeignKey(
        to='mail.MailTemplate', on_delete=models.CASCADE,
        related_name='+', null=True, blank=True,
    )
    reject_template = models.ForeignKey(
        to='mail.MailTemplate', on_delete=models.CASCADE,
        related_name='+', null=True, blank=True,
    )
    # enable_feedback = models.BooleanField(default=False)
    # send_notifications = models.BooleanField(default=True)

    def __str__(self) -> str:
        return str(self.name)

    @property
    def locales(self) -> list:
        return self.locale_array.split(",")

    @property
    def named_locales(self) -> list:
        enabled = set(self.locale_array.split(","))
        return [a for a in settings.LANGUAGES_NATURAL_NAMES if a[0] in enabled]

    def save(self, *args, **kwargs):
        was_created = not bool(self.pk)
        super().save(*args, **kwargs)

        if was_created:
            self._build_initial_data()

    def _get_default_submission_type(self):
        from pretalx.submission.models import Submission, SubmissionType
        sub_type = Submission.objects.filter(event=self).first()
        if not sub_type:
            sub_type = SubmissionType.objects.create(event=self, name='Talk')
        return sub_type

    def _build_initial_data(self):
        from pretalx.mail.default_templates import ACCEPT_TEXT, ACK_TEXT, GENERIC_SUBJECT, REJECT_TEXT
        from pretalx.mail.models import MailTemplate

        if not hasattr(self, 'cfp'):
            from pretalx.submission.models import CfP
            CfP.objects.create(event=self, default_type=self._get_default_submission_type())

        if not self.schedules.filter(version__isnull=True).exists():
            from pretalx.schedule.models import Schedule
            Schedule.objects.create(event=self)

        self.accept_template = self.accept_template or MailTemplate.objects.create(event=self, subject=GENERIC_SUBJECT, text=ACCEPT_TEXT)
        self.ack_template = self.ack_template or MailTemplate.objects.create(event=self, subject=GENERIC_SUBJECT, text=ACK_TEXT)
        self.reject_template = self.reject_template or MailTemplate.objects.create(event=self, subject=GENERIC_SUBJECT, text=REJECT_TEXT)
        self.save()

    @cached_property
    def pending_mails(self):
        return self.queued_mails.count()

    @cached_property
    def wip_schedule(self):
        return self.schedules.get(version__isnull=True)

    def get_mail_backend(self, force_custom: bool=False) -> BaseEmailBackend:
        from pretalx.common.mail import CustomSMTPBackend

        if self.settings.smtp_use_custom or force_custom:
            return CustomSMTPBackend(host=self.settings.smtp_host,
                                     port=self.settings.smtp_port,
                                     username=self.settings.smtp_username,
                                     password=self.settings.smtp_password,
                                     use_tls=self.settings.smtp_use_tls,
                                     use_ssl=self.settings.smtp_use_ssl,
                                     fail_silently=False)
        else:
            return get_connection(fail_silently=False)

    @property
    def event(self):
        return self
