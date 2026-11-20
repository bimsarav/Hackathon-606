from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"

    def ready(self) -> None:
        # Lets ModelForm[Note], ModelSerializer[Note] etc. be subscripted at runtime (needed for strict typing).
        # Runs after settings load; importing DRF inside settings.py would break DRF's settings.
        import django_stubs_ext
        from rest_framework import serializers, viewsets

        django_stubs_ext.monkeypatch(extra_classes=[serializers.ModelSerializer, viewsets.ModelViewSet])
