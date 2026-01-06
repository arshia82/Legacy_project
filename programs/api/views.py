# FILE: myfita/apps/backend/programs/api/views.py

"""
PROGRAM API VIEWS

BP: "coach search/filter API" (memory) - List programs for athletes.
BP: "AI assisted matching" (page 11) - Extend later for rule-based filtering (no ML yet).
"""

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .serializers import ProgramSerializer
from programs.models import Program

class ProgramListView(generics.ListAPIView):
    queryset = Program.objects.all()  # BP: Filter by athlete goals later
    serializer_class = ProgramSerializer
    permission_classes = [IsAuthenticated]  # BP: Athlete privacy (page 1)