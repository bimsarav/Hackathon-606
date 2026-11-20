from django.conf import settings
from django.db import models


class Note(models.Model):
    """Example aggregate. Replace with the product's own domain models."""

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = (models.Index(fields=("owner", "-created_at"), name="note_owner_created_idx"),)

    def __str__(self) -> str:
        return self.title
