from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from rest_framework import viewsets
from rest_framework.serializers import BaseSerializer

from apps.notes.forms import NoteForm
from apps.notes.models import Note
from apps.notes.serializers import NoteSerializer


def _owner(request: HttpRequest) -> User:
    user = request.user
    if not isinstance(user, User):  # guarded by login_required / IsAuthenticated
        raise PermissionError("authenticated user required")
    return user


class NoteViewSet(viewsets.ModelViewSet[Note]):
    """REST API under /api/v1/notes/. Users see and change only their own notes."""

    serializer_class = NoteSerializer

    def get_queryset(self) -> QuerySet[Note]:
        return Note.objects.filter(owner=_owner(self.request))

    def perform_create(self, serializer: BaseSerializer[Note]) -> None:
        serializer.save(owner=_owner(self.request))


@login_required
@require_GET
def notes_page(request: HttpRequest) -> HttpResponse:
    notes = Note.objects.filter(owner=_owner(request))[:50]
    return render(request, "notes/notes.html", {"notes": notes, "form": NoteForm()})


@login_required
@require_POST
def notes_create(request: HttpRequest) -> HttpResponse:
    """htmx endpoint: returns the new list item, or the form with errors (HTTP 422)."""
    form = NoteForm(request.POST)
    if not form.is_valid():
        return render(request, "notes/_form.html", {"form": form}, status=422)
    note = form.save(commit=False)
    note.owner = _owner(request)
    note.save()
    return render(request, "notes/_note_item.html", {"note": note})
