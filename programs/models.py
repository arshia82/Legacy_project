from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class ProgramDelivery(models.Model):
    athlete = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_programs")
    coach = models.ForeignKey(User, on_delete=models.CASCADE, related_name="delivered_programs")
    order_id = models.CharField(max_length=100, unique=True)
    pdf_file = models.FileField(upload_to="programs/pdfs/")
    pdf_hash = models.CharField(max_length=64)
    delivered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["order_id"]),
        ]