from pydantic import BaseModel, EmailStr, Field

class RegisterRequest(BaseModel):
    email: EmailStr

    full_name: str = Field(
        min_length=3,
        max_length=255
    )

    password:str = Field(
        min_length=6,
        max_length=255
    )

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=6,
        max_length=255
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
