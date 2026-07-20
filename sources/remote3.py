"""remote3.co — feed RSS global, se filtra por keywords del perfil.

Nota: el RSS trae solo las ofertas más recientes mezcladas. Filtramos por
título/keywords. Mejorable más adelante con su backend (Supabase).
"""
from __future__ import annotations
from bs4 import BeautifulSoup
from .base import Job, get, parse_dt

RSS = "https://www.remote3.co/api/rss"


def fetch(profile: dict) -> list[Job]:
    try:
        r = get(RSS)
        if r.status_code != 200:
            return []
    except Exception:
        return []

    terms = [t.lower() for t in profile.get("titles", []) + profile.get("keywords_good", [])]
    soup = BeautifulSoup(r.text, "xml")
    jobs: list[Job] = []
    for it in soup.find_all("item"):
        title_raw = (it.title.text if it.title else "").strip()
        low = title_raw.lower()
        if terms and not any(t in low for t in terms):
            continue
        company = ""
        title = title_raw
        if " at " in title_raw:           # formato "Rol at Empresa"
            title, company = title_raw.rsplit(" at ", 1)
        link = it.link.text.strip() if it.link else ""
        if not link:
            continue
        pub = it.find("pubDate")
        jobs.append(Job(
            source="remote3",
            title=title.strip(),
            company=company.strip(),
            url=link,
            location="Remote",
            posted=parse_dt(pub.text if pub else None) or _rss_dt(pub),
            description=(it.description.text[:400] if it.description else ""),
        ))
    return jobs


def _rss_dt(pub):
    if not pub:
        return None
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(pub.text)
    except Exception:
        return None
