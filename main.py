from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.database import engine
from routers.auth_router import router as auth_router
from routers.task_router import router as task_router
from routers.message_router import router as message_router
from routers.user_router import router as user_router
from routers.server_router import router as server_router
from routers.group_task_router import router as group_task_router
from routers.group_message_router import router as group_message_router
from routers.websocket_router import router as websocket_router
from routers.notification_router import router as notification_router
from routers.rating_router import router as rating_router
from utils.error_handlers import register_exception_handlers



@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="TaskMate API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(task_router)
app.include_router(message_router)
app.include_router(user_router)
# mas maaga ang "/server/task" at "/server/messages" kaysa sa server_router: ang "/server/{server_id}" ay hindi dapat makaagaw sa kanila
app.include_router(group_task_router)
app.include_router(group_message_router)
app.include_router(server_router)
app.include_router(websocket_router)
app.include_router(notification_router)
app.include_router(rating_router)


@app.get("/")
def root():
    return {"status": "ok"}