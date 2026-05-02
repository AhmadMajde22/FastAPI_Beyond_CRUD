from passlib.context import CryptContext
from datetime import timedelta, datetime
import jwt
from src.config import Config
import uuid
import logging
from itsdangerous import URLSafeTimedSerializer

JWT_SECRET = Config.JWT_SECRET
JWT_ALGORITHM = Config.JWT_ALGORITHM

ACCESS_TOKEN_EXPIRY = 3600

passwd_context = CryptContext(schemes=["bcrypt"])

serializer = URLSafeTimedSerializer(secret_key=Config.JWT_SECRET,salt="email-configuration")

def generate_password_hash(password: str) -> str:
    hash = passwd_context.hash(password)

    return hash


def verify_password(password: str, hash: str) -> bool:
    return passwd_context.verify(password, hash)


def create_access_token(
    user_data: dict, expiry: timedelta = None, refresh: bool = False
):

    payload = {}

    payload["user"] = user_data
    payload["exp"] = datetime.now() + (
        expiry if expiry else timedelta(seconds=ACCESS_TOKEN_EXPIRY)
    )
    payload["jti"] = str(uuid.uuid4())

    payload["refresh"] = refresh

    token = jwt.encode(payload=payload, key=JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_token(token) -> dict:
    try:
        token_data = jwt.decode(jwt=token, key=JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return token_data

    except jwt.PyJWTError as e:
        logging.exception(e)
        return None


def create_url_safe_token(data:dict):

    token = serializer.dumps(data)

    return token


def decode_url_safe_token(token: str) -> dict:
    try:
        return serializer.loads(token)
    except Exception as e:
        logging.error(str(e))
        from src.errors import InvalidToken
        raise InvalidToken()
