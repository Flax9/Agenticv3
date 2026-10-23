import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Role


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("username", "password")
    @classmethod
    def _no_nul(cls, value: str) -> str:
        # PostgreSQL menolak karakter NUL pada teks (galat 500 bila lolos sampai query)
        if "\x00" in value:
            raise ValueError("Karakter NUL tidak diizinkan.")
        return value


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    nama_lengkap: str
    jabatan: str | None
    role: Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # detik
    user: UserProfile
