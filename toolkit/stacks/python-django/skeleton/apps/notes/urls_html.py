from django.urls import path

from apps.notes import views

urlpatterns = [
    path("", views.notes_page, name="notes"),
    path("create", views.notes_create, name="notes-create"),
]
