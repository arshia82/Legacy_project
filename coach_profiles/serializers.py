from rest_framework import serializers
from .models import CoachProfile


class CoachProfilePublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachProfile
        fields = ["id", "expertise", "bio"]


class CoachProfilePrivateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoachProfile
        fields = "__all__"