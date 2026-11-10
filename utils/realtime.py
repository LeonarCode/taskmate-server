from fastapi import BackgroundTasks
from models import Notification
from schemas.notification_schema import NotificationResponse
from utils.connection_manager import manager


async def _send_events(events: list[tuple[int, dict]]) -> None:
    for user_id, payload in events:
        await manager.send_to_user(user_id, payload)


def push_notifications(background_tasks: BackgroundTasks, notifications: Notification | list[Notification]) -> None:
    """Itulak ang bagong notification sa bukas na socket ng may-ari (event na "notification").

    Isang linya pagkatapos ng notify / notify_many:
        push_notifications(background_tasks, await service.notify(...))

    Isinasalin dito agad ang laman (habang bukas pa ang DB), at ang pagpapadala ay pagkatapos ng response,
    kaya hindi maaantala ang request at walang DB sa background. Ang offline na user ay makikita ito sa GET /notifications.
    """
    if isinstance(notifications, Notification):
        notifications = [notifications]
    if not notifications:  # walang nagawa (hal. walang ibang member), walang ipapadala
        return
    events = [
        (n.user_id, {"type": "notification", "data": NotificationResponse.model_validate(n).model_dump(mode="json")})
        for n in notifications
    ]
    background_tasks.add_task(_send_events, events)
