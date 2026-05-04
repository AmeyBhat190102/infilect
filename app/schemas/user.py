import re
from typing import Optional
from pydantic import BaseModel, field_validator

VALID_USER_TYPES = {1, 2, 3, 7}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[\d\s\-().]{7,32}$")


class UserRow(BaseModel):
    """
    Represents one validated row from users_master.csv.
    """

    username: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    email: str
    user_type: Optional[int] = 1
    phone_number: Optional[str] = ""
    supervisor_username: Optional[str] = None   # resolved to FK in service
    is_active: Optional[bool] = True

    # ------------------------------------------------------------------ #
    # Required fields
    # ------------------------------------------------------------------ #
    @field_validator("username", "email", mode="before")
    @classmethod
    def not_blank(cls, v, info) -> str:
        if v is None or str(v).strip() == "":
            raise ValueError(f"{info.field_name} is required and cannot be blank")
        return str(v).strip()

    # ------------------------------------------------------------------ #
    # Length limits
    # ------------------------------------------------------------------ #
    @field_validator("username", "first_name", "last_name", mode="before")
    @classmethod
    def max_150(cls, v, info) -> Optional[str]:
        if v is None:
            return ""
        v = str(v).strip()
        if len(v) > 150:
            raise ValueError(f"{info.field_name} exceeds 150 characters")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def max_254(cls, v) -> str:
        v = str(v).strip()
        if len(v) > 254:
            raise ValueError("email exceeds 254 characters")
        return v

    @field_validator("phone_number", mode="before")
    @classmethod
    def max_32(cls, v) -> str:
        if v is None:
            return ""
        v = str(v).strip()
        if len(v) > 32:
            raise ValueError("phone_number exceeds 32 characters")
        return v

    # ------------------------------------------------------------------ #
    # Format checks
    # ------------------------------------------------------------------ #
    @field_validator("email", mode="after")
    @classmethod
    def valid_email(cls, v: str) -> str:
        if not EMAIL_RE.match(v):
            raise ValueError(f"'{v}' is not a valid email address")
        return v

    @field_validator("phone_number", mode="after")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        if v and not PHONE_RE.match(v):
            raise ValueError(f"'{v}' is not a valid phone number")
        return v

    # ------------------------------------------------------------------ #
    # Enum check
    # ------------------------------------------------------------------ #
    @field_validator("user_type", mode="before")
    @classmethod
    def valid_user_type(cls, v) -> int:
        if v is None or str(v).strip() == "":
            return 1
        try:
            val = int(float(str(v).strip()))
        except (ValueError, TypeError):
            raise ValueError(f"user_type must be one of {VALID_USER_TYPES}")
        if val not in VALID_USER_TYPES:
            raise ValueError(f"user_type '{val}' must be one of {VALID_USER_TYPES}")
        return val

    @field_validator("is_active", mode="before")
    @classmethod
    def coerce_bool(cls, v) -> bool:
        if isinstance(v, bool):
            return v
        if v is None or str(v).strip() == "":
            return True
        return str(v).strip().lower() in ("true", "1", "yes", "y")
