from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from config.database import get_db
from utils.auth_dependency import get_current_user
from utils.mailer import send_password_reset_email
from models import User
from schemas.user_schema import (
    UserCreate, UserLogin, UserResponse, GoogleLogin, GoogleRegister, Token, Availability,
    ForgotPassword, ResetPassword, OkResponse
)
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


# Register screen: i-check ang email bago pumunta sa Complete Profile
@router.get("/check-email", response_model=Availability)
async def check_email(email: EmailStr, service: AuthService = Depends(get_auth_service)):
    return Availability(available=not await service.email_taken(email))


# Complete Profile screen: i-check ang username habang nagta-type
@router.get("/check-username", response_model=Availability)
async def check_username(
    username: str = Query(min_length=1, max_length=255),
    service: AuthService = Depends(get_auth_service),
):
    return Availability(available=not await service.username_taken(username))


# Complete Setup (email): isang tawag lang, dala ang email/password mula sa unang screen
@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, service: AuthService = Depends(get_auth_service)):
    return await service.register(data)


# Sign In tab
@router.post("/login", response_model=Token)
async def login(data: UserLogin, service: AuthService = Depends(get_auth_service)):
    return await service.login(data)


# Continue with Google: 404 "user_not_found" = bagong user, ipakita ang Complete Profile
@router.post("/google", response_model=Token)
async def google_login(data: GoogleLogin, service: AuthService = Depends(get_auth_service)):
    return await service.google_login(data)


# Complete Setup (Google)
@router.post("/google/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def google_register(data: GoogleRegister, service: AuthService = Depends(get_auth_service)):
    return await service.google_register(data)


# Forgot password, hakbang 1: ipadala ang 6-digit code sa email. Laging pareho ang sagot (hindi malalaman kung may account)
@router.post("/forgot-password", response_model=OkResponse)
async def forgot_password(
    data: ForgotPassword,
    background_tasks: BackgroundTasks,
    service: AuthService = Depends(get_auth_service),
):
    to_send = await service.forgot_password(data.email)
    if to_send:
        background_tasks.add_task(send_password_reset_email, *to_send)  # pagkatapos ng response, para pareho ang bilis
    return OkResponse(message="If that email is registered, we sent a 6-digit code.")


# Forgot password, hakbang 2: code + bagong password. 400 "invalid_code" kapag mali o expired
@router.post("/reset-password", response_model=OkResponse)
async def reset_password(data: ResetPassword, service: AuthService = Depends(get_auth_service)):
    await service.reset_password(data.email, data.code, data.new_password)
    return OkResponse(message="Password updated. You can log in now.")


# pagbukas ng app: may naka-save na token, kunin ang profile
@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
