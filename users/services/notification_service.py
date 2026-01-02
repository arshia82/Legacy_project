# users/services/notification_service.py

def notify_user(*, phone=None, sms=None, user=None, in_app=None):
    """
    Lightweight notification dispatcher.
    Async-ready, safe for MVP.
    """
    if sms and phone:
        _send_sms(phone, sms)

    if in_app and user:
        _send_in_app(user, in_app)


def _send_sms(phone, message):
    # Placeholder for Kavenegar / async worker
    print(f"[SMS to {phone}] {message}")


def _send_in_app(user, message):
    # Placeholder for in-app notifications
    print(f"[IN-APP to {user}] {message}")