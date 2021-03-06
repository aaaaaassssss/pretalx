from django.http import JsonResponse
from django.views.generic import TemplateView, View
from i18nfield.utils import I18nJSONEncoder


class ScheduleView(TemplateView):
    template_name = 'orga/schedule/index.html'


class RoomList(View):

    def get(self, request, event):
        return JsonResponse({
            'start': request.event.date_from,
            'end': request.event.date_to,
            'rooms': [
                {
                    'id': room.pk,
                    'name': room.name,
                    'description': room.description,
                    'capacity': room.capacity,
                }
                for room in request.event.rooms.order_by('position')
            ]
        }, encoder=I18nJSONEncoder)


class TalkList(View):

    def get(self, request, event):
        schedule = request.event.wip_schedule
        return JsonResponse({'results': [
            {
                'title': slot.submission.title,
                'speakers': [
                    {'name': speaker.name, 'nick': speaker.nick}
                    for speaker in slot.submission.speakers.all()
                ],
                'submission_type': slot.submission.submission_type.name,
                'state': slot.submission.state,
                'description': slot.submission.description,
                'abstract': slot.submission.abstract,
                'notes': slot.submission.notes,
                'duration': slot.submission.duration or slot.submission.submission_type.default_duration,
                'content_locale': slot.submission.content_locale,
                'do_not_record': slot.submission.do_not_record,
                'room': slot.room.pk if slot.room else None,
                'start': slot.start,
                'end': slot.end,
            }
            for slot in schedule.talks.all()
        ]}, encoder=I18nJSONEncoder)


class TalkUpdate(View):

    def patch(self, request, event, pk):
        pass
