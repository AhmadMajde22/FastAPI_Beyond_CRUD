from fastapi import APIRouter, Depends, HTTPException, status,BackgroundTasks
from .schemas import (
    UserCreateModel,
    UserModel,
    UserLoginModel,
    UserBooksModel,
    EmailModel,
    PasswordRestRequestModel,
    PasswordRestConfirmModel,
)
from .services import UserService
from src.db.main import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from .utils import (
    create_access_token,
    verify_password,
    generate_password_hash,
    create_url_safe_token,
    decode_url_safe_token,
)
from datetime import timedelta, datetime
import logging
from fastapi.responses import JSONResponse
from .dependencies import RefreshTokenBearer, AccessTokenBearer, get_current_user, RoleChecker  # type: ignore
from src.db.redis import add_jti_to_blocklist
from src.errors import UserNotFound, UserAlreadyExists, InvalidCredentials, InvalidToken
from src.mail import create_message, mail
from src.config import Config
from src.celery_tasks import send_email


REFRESH_TOKEN_EXPIRY = 2

auth_router = APIRouter()

user_service = UserService()

role_checker = RoleChecker(["admin", "user"])

access_token_bearer = AccessTokenBearer()
refresh_token_bearer = RefreshTokenBearer()


@auth_router.post(
    "/send_mail",
    responses={
        200: {"description": "Email queued for delivery"},
        400: {"description": "Malformed request body"},
    },
)
async def send_mail(emails: EmailModel):
    emails = emails.addresses  # type: ignore

    html = "<h1>Welcome to the App </h1>"

    subject = "Welcome to our App"

    send_email.delay(emails,subject,html)

    return {"message": "Email snet successfully"}


@auth_router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "User account created"},
        400: {"description": "Malformed request body"},
        403: {"description": "User with email already exists"},
    },
)
async def create_user_account(
    user_data: UserCreateModel, bg_tasks:BackgroundTasks,session: AsyncSession = Depends(get_session)
):
    email = user_data.email

    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise UserAlreadyExists()

    new_user = await user_service.create_user(user_data, session)

    token = create_url_safe_token({"email": email})

    link = f"http://{Config.DOMAIN}/api/v1/auth/verify/{token}"
    html = f"""
    <h1> Verify Your Email </h1>
    <p> Please click this <a href="{link}">Link</a> to verify your email</p>
    """


    emails = [email]

    subject = "Verify you email"
    send_email.delay(emails, subject, html)

    return {
        "message": "Acount created! Check email to verify your account",
        "user": new_user,
    }


@auth_router.get(
    "/verify/{token}",
    responses={
        200: {"description": "Account verified successfully"},
        401: {"description": "Invalid or expired token"},
        404: {"description": "User not found"},
    },
)
async def verify_user_account(token: str, session: AsyncSession = Depends(get_session)):
    token_data = decode_url_safe_token(token)

    user_email = token_data.get("email")

    if not user_email:
        raise InvalidToken()

    user = await user_service.get_user_by_email(user_email, session)

    if not user:
        raise UserNotFound()

    await user_service.update_user(user, {"is_verified": True}, session)

    return JSONResponse(
        content={"message": "Acount verified successfully"},
        status_code=status.HTTP_200_OK,
    )


@auth_router.post(
    "/login",
    responses={
        200: {"description": "Login successful"},
        400: {"description": "Malformed request body"},
        401: {"description": "Invalid email or password"},
    },
)
async def login_users(
    login_data: UserLoginModel, session: AsyncSession = Depends(get_session)
):
    email = login_data.email
    password = login_data.password

    user = await user_service.get_user_by_email(email, session)

    if user:
        password_valid = verify_password(password, user.password_hash)

        if password_valid:
            access_token = create_access_token(
                user_data={
                    "email": user.email,
                    "user_uid": str(user.uid),
                    "role": user.role,
                }
            )

            refresh_token = create_access_token(
                user_data={"email": user.email, "user_uid": str(user.uid)},
                refresh=True,
                expiry=timedelta(days=REFRESH_TOKEN_EXPIRY),
            )

            return JSONResponse(
                content={
                    "message": "login successful",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {"email": user.email, "uid": str(user.uid)},
                }
            )
    raise InvalidCredentials()


@auth_router.get(
    "/refresh_token",
    responses={
        200: {"description": "New access token issued"},
        401: {"description": "Invalid, expired, or revoked token"},
        403: {"description": "Refresh token required"},
    },
)
async def get_new_access_token(token_details: dict = Depends(refresh_token_bearer)):

    expiry_timestamp = token_details["exp"]

    if datetime.fromtimestamp(expiry_timestamp) > datetime.now():

        new_access_token = create_access_token(user_data=token_details["user"])

        return JSONResponse(content={"access_token": new_access_token})

    raise InvalidToken()


@auth_router.get(
    "/me",
    response_model=UserBooksModel,
    responses={
        200: {"description": "Current user details"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions or account not verified"},
    },
)
async def get_current_user(
    user=Depends(get_current_user), _: bool = Depends(role_checker)
):
    return user


@auth_router.get(
    "/logout",
    responses={
        200: {"description": "Logged out successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Refresh token sent when access token required"},
    },
)
async def revoke_token(token_details: dict = Depends(access_token_bearer)):

    jti = token_details["jti"]

    await add_jti_to_blocklist(jti)

    return JSONResponse(
        {"message": "Logged Out Successfully"}, status_code=status.HTTP_200_OK
    )


@auth_router.post(
    "/password_reset_request",
    responses={
        200: {"description": "Password reset email queued"},
    },
)
async def password_rest_request(email_data: PasswordRestRequestModel):
    email = email_data.email

    token = create_url_safe_token({"email": email})

    link = f"http://{Config.DOMAIN}/api/v1/auth/password_reset_confirm/{token}"
    html_message = f"""
    <h1> Rest Your Password </h1>
    <p> Please click this <a href="{link}">Link</a> to reset your password</p>
    """

    message = create_message(
        recipients=[email], subject="Reset you Passwoord", body=html_message
    )

    try:
        await mail.send_message(message)
    except Exception as e:
        logging.error(f"Failed to send password reset email: {e}")

    return JSONResponse(
        content={
            "message": "please check your email to reset your password",
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.post(
    "/password_reset_confirm/{token}",
    responses={
        200: {"description": "Password reset successfully"},
        400: {"description": "Passwords do not match"},
        401: {"description": "Invalid or expired token"},
        404: {"description": "User not found"},
    },
)
async def reset_account_password(
    token: str,
    passwords: PasswordRestConfirmModel,
    session: AsyncSession = Depends(get_session),
):

    new_password = passwords.new_password
    confirm_password = passwords.confirm_new_password

    if new_password != confirm_password:
        raise HTTPException(
            detail="Passords don't match", status_code=status.HTTP_400_BAD_REQUEST
        )

    token_data = decode_url_safe_token(token)

    user_email = token_data.get("email")

    if not user_email:
        raise InvalidToken()

    user = await user_service.get_user_by_email(user_email, session)

    if not user:
        raise UserNotFound()

    passwd_hash = generate_password_hash(new_password)
    await user_service.update_user(user, {"password_hash": passwd_hash}, session)

    return JSONResponse(
        content={"message": "Password Reset Sucessfully "},
        status_code=status.HTTP_200_OK,
    )
