from coach_profiles.models import CoachMedia

def revoke_media_for_user(profile):
    CoachMedia.objects.filter(profile=profile, is_deleted=False).update(is_deleted=True)