from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from utils.auth_dependency import get_current_user_ws
from utils.connection_manager import manager
from models import User

router = APIRouter(tags=["websocket"])


# Real-time ng buong app. Server papunta sa app lang ang daloy: sa REST pa rin nagpapadala ang app (may validation at error),
# at pagkatapos ay itinutulak dito ang event sa ibang tao. Isang socket lang bawat device, para sa lahat ng uri ng event.
#
#   ws://.../ws  ·  header: Authorization: Bearer <token>  (o ?token=<token>, pero lumalabas iyon sa access log)
#
# Mga event, laging {"type": ..., "data": ...}:
#   DM:          "message", "message_edited" (buong mensahe) · "message_deleted" {"id"} · "read" {"reader_id"}
#   Group chat:  "group_message", "group_message_edited" (buong mensahe, may server_id) · "group_message_deleted" {"id", "server_id"}
#   Alerts:      "notification" (buong notification, tulad ng sa GET /notifications) ·
#                "notification_read" {"id"} · "notifications_read_all" {} · "notification_deleted" {"id"} · "notifications_cleared" {}
#                (ang apat na huli ay para magkapareho ang badge sa lahat ng device ng user)
#
# Heartbeat: magpadala ang app ng "ping" at sasagot ng "pong", para hindi putulin ng network ang koneksyon
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user: User | None = Depends(get_current_user_ws)):
    if user is None:  # walang token, mali, expired, o nabura na ang user
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await manager.connect(user.id, websocket)
    try:
        while True:
            if await websocket.receive_text() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user.id, websocket)
