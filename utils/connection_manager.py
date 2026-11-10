import asyncio
from fastapi import WebSocket


class ConnectionManager:
    """Mga bukas na WebSocket ng bawat user (puwedeng higit sa isa, hal. dalawang device).

    Nasa memory ito ng iisang process lang: kung higit sa isang uvicorn worker ang gagamitin,
    kailangan ng Redis pub/sub para maabot ang user na nakakonekta sa ibang worker.
    """

    def __init__(self):
        self.active: dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        sockets = self.active.get(user_id)
        if sockets is None:
            return
        sockets.discard(websocket)
        if not sockets:
            del self.active[user_id]

    async def send_to_user(self, user_id: int, payload: dict) -> None:
        for websocket in list(self.active.get(user_id, ())):
            try:
                await websocket.send_json(payload)
            except Exception:  # patay na ang koneksyon; huwag guluhin ang iba
                self.disconnect(user_id, websocket)

    async def send_to_users(self, user_ids: list[int], payload: dict) -> None:
        # sabay-sabay: hindi maaantala ang lahat ng isang mabagal na koneksyon
        await asyncio.gather(*(self.send_to_user(user_id, payload) for user_id in user_ids))


manager = ConnectionManager()
