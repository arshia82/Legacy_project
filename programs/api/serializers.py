# FILE: myfita/apps/backend/programs/api/serializers.py

"""
PROGRAM SERIALIZERS

BP: "program purchase delivery (PDF)" (page 3) - Serialize for API listing/purchase.
BP: "platform commission on program sales (average 12% of GMV)" (page 4) - Include price for calc.
"""

from rest_framework import serializers
from programs.models import Program  # Assuming Program model exists (create if needed)

class ProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = Program
        fields = ['id', 'title', 'description', 'price', 'coach']  # BP: Expose for athlete search
        read_only_fields = ['coach']  # BP: Athlete privacy (page 1)