from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _

from pretalx.common.choices import Choices
from pretalx.common.mixins import LogMixin
from pretalx.mail.context import template_context_from_submission


class SubmissionError(Exception):
    pass


class SubmissionStates(Choices):
    SUBMITTED = 'submitted'
    REJECTED = 'rejected'
    ACCEPTED = 'accepted'
    CONFIRMED = 'confirmed'
    CANCELED = 'canceled'
    WITHDRAWN = 'withdrawn'

    valid_choices = [
        (SUBMITTED, _('submitted')),
        (REJECTED, _('rejected')),
        (ACCEPTED, _('accepted')),
        (CONFIRMED, _('confirmed')),
        (CANCELED, _('canceled')),
        (WITHDRAWN, _('withdrawn'))
    ]

    valid_next_states = {
        SUBMITTED: (REJECTED, WITHDRAWN, ACCEPTED),
        REJECTED: (ACCEPTED, SUBMITTED),
        ACCEPTED: (CONFIRMED, CANCELED, REJECTED, SUBMITTED),
        CONFIRMED: (ACCEPTED, CANCELED),
        WITHDRAWN: (SUBMITTED,)
    }


class Submission(LogMixin, models.Model):
    code = models.CharField(
        max_length=16,
        db_index=True
    )
    speakers = models.ManyToManyField(
        to='person.User',
        related_name='submissions',
        blank=True,
    )
    event = models.ForeignKey(
        to='event.Event',
        on_delete=models.PROTECT,
        related_name='submissions',
    )
    title = models.CharField(
        verbose_name=_('Title'),
        max_length=200,
    )
    submission_type = models.ForeignKey(  # Reasonable default must be set in form/view
        verbose_name=_('Type of submission'),
        to='submission.SubmissionType',
        related_name='submissions',
        on_delete=models.PROTECT,
    )
    state = models.CharField(
        verbose_name=_('Submission state'),
        max_length=SubmissionStates.get_max_length(),
        choices=SubmissionStates.get_choices(),
        default=SubmissionStates.SUBMITTED,
    )
    description = models.TextField(
        verbose_name=_('Description'),
        null=True, blank=True,
    )
    abstract = models.TextField(
        verbose_name=_('Abstract'),
        null=True, blank=True,
    )
    notes = models.TextField(
        verbose_name=_('Notes for the organizer'),
        null=True, blank=True,
    )
    duration = models.PositiveIntegerField(
        null=True, blank=True
    )
    content_locale = models.CharField(max_length=32, default=settings.LANGUAGE_CODE,
                                      choices=settings.LANGUAGES,
                                      verbose_name=_('Language of the submission'))
    do_not_record = models.BooleanField(
        default=False,
        verbose_name=_('Don\'t record my talk.')
    )

    def assign_code(self):
        # This omits some character pairs completely because they are hard to read even on screens (1/I and O/0)
        # and includes only one of two characters for some pairs because they are sometimes hard to distinguish in
        # handwriting (2/Z, 4/A, 5/S, 6/G).
        charset = list('ABCDEFGHJKLMNPQRSTUVWXYZ3789')
        while True:
            code = get_random_string(length=6, allowed_chars=charset)
            if not Submission.objects.filter(code=code).exists():
                self.code = code
                return

    def save(self, *args, **kwargs):
        if not self.code:
            self.assign_code()
        super().save(*args, **kwargs)

    @property
    def editable(self):
        return self.state in (
            SubmissionStates.ACCEPTED, SubmissionStates.CONFIRMED, SubmissionStates.SUBMITTED
        ) and self.event.cfp.is_open

    def accept(self, person=None, force=False):
        if self.state not in [SubmissionStates.SUBMITTED, SubmissionStates.REJECTED] and not force:
            raise SubmissionError(f'Submission must be submitted or rejected, not {self.state} to be accepted.')

        self.state = SubmissionStates.ACCEPTED
        self.save(update_fields=['state'])
        self.log_action('pretalx.submission.accept', person=person, orga=True)

        from pretalx.schedule.models import TalkSlot
        TalkSlot.objects.create(submission=self, schedule=self.event.wip_schedule)

        for speaker in self.speakers.all():
            self.event.accept_template.to_mail(
                user=speaker, event=self.event, context=template_context_from_submission(self),
                locale=speaker.locale
            )

    def reject(self, person=None):
        self.state = SubmissionStates.REJECTED
        self.save(update_fields=['state'])
        self.log_action('pretalx.submission.reject', person=person, orga=True)

        from pretalx.schedule.models import TalkSlot
        TalkSlot.objects.filter(submission=self, schedule=self.event.wip_schedule).delete()

        for speaker in self.speakers.all():
            self.event.accept_template.to_mail(
                user=speaker, event=self.event, context=template_context_from_submission(self),
                locale=speaker.locale
            )

    def __str__(self):
        return self.title


class SubmissionAttachment:
    pass
