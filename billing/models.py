from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class CoachPackage(models.Model):
    name = models.CharField(max_length=50)
    max_presets = models.PositiveIntegerField()
    price_toman = models.PositiveIntegerField()

class CoachSubscription(models.Model):
    coach = models.OneToOneField(User, on_delete=models.CASCADE)
    package = models.ForeignKey(CoachPackage, on_delete=models.PROTECT)