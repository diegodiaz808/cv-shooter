"""Tipos y helpers compartidos por todas las fuentes."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import re
import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    )
}


@dataclass
class Job:
    source: str
    title: str
    company: str
    url: str
    location: str = ""
    salary: str = ""
    tags: list[str] = field(default_factory=list)
    posted: datetime | None = None      # tz-aware UTC
    description: str = ""
    seniority: str = ""                 # ej "entry level", "associate" (LinkedIn)
    easy_apply: bool | None = None      # True=Easy Apply, False=sitio externo
    workplace: str = ""                 # remote | hybrid | on-site (LinkedIn)

    @property
    def uid(self) -> str:
        """ID estable para deduplicar (mismo título+empresa = misma aplicación).
        Así se colapsan reposts de LinkedIn con distinto ID/URL, dentro de una
        corrida y entre corridas (historial)."""
        key = re.sub(r"\s+", " ", f"{self.title}|{self.company}".lower()).strip()
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]

    @property
    def haystack(self) -> str:
        """Texto sobre el que corre el matching de keywords."""
        return " ".join([self.title, self.company, " ".join(self.tags),
                          self.description]).lower()


def get(url: str, **kw) -> requests.Response:
    kw.setdefault("headers", HEADERS)
    kw.setdefault("timeout", 25)
    return requests.get(url, **kw)


def parse_dt(value) -> datetime | None:
    """Parsea fechas variadas a datetime tz-aware UTC."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # epoch ms o s
        v = value / 1000 if value > 1e12 else value
        return datetime.fromtimestamp(v, tz=timezone.utc)
    s = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S %z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
