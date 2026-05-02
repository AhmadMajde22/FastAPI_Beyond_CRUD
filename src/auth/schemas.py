from typing import List

from pydantic import BaseModel, EmailStr, Field
import uuid
from datetime import datetime
from src.books.schemas import Book
from src.reviews.schemas import ReviewModel


class UserCreateModel(BaseModel):
    username: str = Field(max_length=16)
    email: EmailStr = Field(max_length=40)
    password: str = Field(min_length=6)
    first_name: str = Field(max_length=25)
    last_name: str = Field(max_length=25)


class UserModel(BaseModel):
    uid: uuid.UUID
    username: str
    email: str
    password_hash: str = Field(exclude=True)
    first_name: str
    last_name: str
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class UserBooksModel(UserModel):
    books: List[Book]
    reviews: List[ReviewModel]


class UserLoginModel(BaseModel):
    email: EmailStr = Field(max_length=40)
    password: str = Field(min_length=6)


class EmailModel(BaseModel):
    addresses: List[str]


class PasswordRestRequestModel(BaseModel):
    email: EmailStr



class PasswordRestConfirmModel(BaseModel):
    new_password: str
    confirm_new_password: str
