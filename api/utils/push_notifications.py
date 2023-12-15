from firebase_admin import messaging


def send_push_notification(token, title, body, data):

    if token is not None:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=token,
            data=data
        )
        messaging.send(message)
