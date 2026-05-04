from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, field_validator


def _parse_date_str(v) -> Optional[date]:
    if v is None or str(v).strip() in ("", "nan", "NaT"):
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"'{v}' is not a recognised date format (expected YYYY-MM-DD)")


class PJPRow(BaseModel):
    """
    Represents one validated row from store_user_mapping.csv.
    username and store_id are resolved to FKs in the service layer.
    The CSV column 'date' is mapped to 'visit_date' to avoid shadowing
    Python's datetime.date type in Pydantic v2 validators.
    """

    username: str
    store_id: str
    visit_date: Optional[date] = None
    is_active: Optional[bool] = True

    @field_validator("username", "store_id", mode="before")
    @classmethod
    def not_blank(cls, v, info) -> str:
        if v is None or str(v).strip() == "":
            raise ValueError(f"{info.field_name} is required and cannot be blank")
        return str(v).strip()

    @field_validator("visit_date", mode="before")
    @classmethod
    def parse_date(cls, v) -> Optional[date]:
        return _parse_date_str(v)

    @field_validator("is_active", mode="before")
    @classmethod
    def coerce_bool(cls, v) -> bool:
        if isinstance(v, bool):
            return v
        if v is None or str(v).strip() == "":
            return True
        return str(v).strip().lower() in ("true", "1", "yes", "y")

    @classmethod
    def from_csv_row(cls, raw: dict) -> "PJPRow":
        """
        Factory that accepts a raw CSV dict where the date column is called 'date'.
        Maps 'date' -> 'visit_date' transparently.
        """
        mapped = dict(raw)
        if "date" in mapped and "visit_date" not in mapped:
            mapped["visit_date"] = mapped.pop("date")
        return cls(**mapped)
