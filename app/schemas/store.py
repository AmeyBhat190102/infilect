from pydantic import BaseModel, field_validator, model_validator
from typing import Optional


class StoreRow(BaseModel):
    """
    Represents one validated row from stores_master.csv.
    All fields come in as strings from the CSV reader; we coerce here.
    """

    store_id: str
    store_external_id: Optional[str] = ""
    name: str
    title: str
    store_brand: Optional[str] = None
    store_type: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    latitude: Optional[float] = 0.0
    longitude: Optional[float] = 0.0
    is_active: Optional[bool] = True

    # ------------------------------------------------------------------ #
    # Required-field guards
    # ------------------------------------------------------------------ #
    @field_validator("store_id", "name", "title", mode="before")
    @classmethod
    def not_blank(cls, v: str, info) -> str:
        if v is None or str(v).strip() == "":
            raise ValueError(f"{info.field_name} is required and cannot be blank")
        return str(v).strip()

    # ------------------------------------------------------------------ #
    # Length limits (mirror VARCHAR lengths in schema)
    # ------------------------------------------------------------------ #
    @field_validator("store_id", "store_external_id", "name", "title",
                     "store_brand", "store_type", "city", "state", "country", "region",
                     mode="before")
    @classmethod
    def max_255(cls, v, info) -> Optional[str]:
        if v is None:
            return v
        v = str(v).strip()
        if len(v) > 255:
            raise ValueError(f"{info.field_name} exceeds 255 characters")
        return v

    # ------------------------------------------------------------------ #
    # Lat / lon range
    # ------------------------------------------------------------------ #
    @field_validator("latitude", mode="before")
    @classmethod
    def valid_latitude(cls, v) -> float:
        if v is None or str(v).strip() in ("", "nan"):
            return 0.0
        try:
            f = float(v)
        except (ValueError, TypeError):
            raise ValueError("latitude must be a number")
        if not (-90.0 <= f <= 90.0):
            raise ValueError("latitude must be between -90 and 90")
        return f

    @field_validator("longitude", mode="before")
    @classmethod
    def valid_longitude(cls, v) -> float:
        if v is None or str(v).strip() in ("", "nan"):
            return 0.0
        try:
            f = float(v)
        except (ValueError, TypeError):
            raise ValueError("longitude must be a number")
        if not (-180.0 <= f <= 180.0):
            raise ValueError("longitude must be between -180 and 180")
        return f

    # ------------------------------------------------------------------ #
    # Boolean coercion (CSV may have "True"/"False"/"1"/"0"/"yes"/"no")
    # ------------------------------------------------------------------ #
    @field_validator("is_active", mode="before")
    @classmethod
    def coerce_bool(cls, v) -> bool:
        if isinstance(v, bool):
            return v
        if v is None or str(v).strip() == "":
            return True
        return str(v).strip().lower() in ("true", "1", "yes", "y")
