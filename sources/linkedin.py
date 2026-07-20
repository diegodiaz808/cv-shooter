"""LinkedIn — endpoint público 'jobs-guest' (sin login).

Nota: LinkedIn limita el scraping. Usamos el endpoint guest con pausas y
pocas páginas por keyword para no gatillar bloqueos. Si empieza a devolver
429/403, bajá la cantidad de títulos o esperá un rato.
"""
from __future__ import annotations
import re
import time
import urllib.parse
from bs4 import BeautifulSoup
from .base import Job, get, parse_dt

API = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/"
PAGES = 2            # páginas por keyword (10 ofertas c/u)
PAUSE = 1.5         # segundos entre requests (cuidar rate-limit)

_ID = re.compile(r"(\d{6,})")


def _job_id(href: str) -> str | None:
    """Extrae el ID numérico de la oferta (único entre subdominios/slugs)."""
    m = _ID.search(href.split("?")[0])
    return m.group(1) if m else None


def _clean_url(href: str) -> str:
    """URL canónica por ID, para dedup estable entre corridas y subdominios."""
    jid = _job_id(href)
    if jid:
        return f"https://www.linkedin.com/jobs/view/{jid}/"
    return href.split("?")[0]


def enrich(job: Job) -> Job:
    """Trae detalle de la oferta: seniority + si es Easy Apply (onsite)."""
    jid = _job_id(job.url)
    if not jid:
        return job
    try:
        r = get(DETAIL + jid)
        if r.status_code != 200:
            return job
    except Exception:
        return job
    html = r.text
    s = BeautifulSoup(html, "lxml")
    # Easy Apply: el botón de aplicar es 'onsite' (dentro de LinkedIn)
    if "apply-link-onsite" in html:
        job.easy_apply = True
    elif "apply-link-offsite" in html:
        job.easy_apply = False
    # Seniority level
    for c in s.select(".description__job-criteria-item, .job-criteria__item"):
        txt = " ".join(c.get_text(" ", strip=True).split()).lower()
        if "seniority level" in txt:
            job.seniority = txt.replace("seniority level", "").strip()
            break
    # Workplace type: on-site / hybrid / remote (aparece en el detalle)
    low = html.lower()
    if "hybrid" in low:
        job.workplace = "hybrid"
    elif "on-site" in low or "onsite" in low:
        job.workplace = "on-site"
    elif "remote" in low or "telecommute" in low:
        job.workplace = "remote"
    time.sleep(PAUSE)
    return job


def fetch(profile: dict) -> list[Job]:
    jobs: list[Job] = []
    seen: set[str] = set()
    location = profile.get("location", "Worldwide")
    # qué buscar en LinkedIn: linkedin_queries si está, si no los titles
    queries = profile.get("linkedin_queries") or profile.get("titles", [])
    for kw in queries:
        for page in range(PAGES):
            params = {
                "keywords": kw,
                "location": location,
                "f_WT": "2",            # 2 = remoto
                "f_TPR": "r604800",     # últimos 7 días
                "start": str(page * 10),
            }
            url = f"{API}?{urllib.parse.urlencode(params)}"
            try:
                r = get(url)
                if r.status_code != 200:
                    break
            except Exception:
                break
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.select("li")
            if not cards:
                break
            for li in cards:
                a = li.select_one("a[href]")
                t = li.select_one("h3")
                c = li.select_one("h4")
                tm = li.select_one("time")
                if not a or not t:
                    continue
                link = _clean_url(a.get("href", ""))
                if not link or link in seen:
                    continue
                seen.add(link)
                jobs.append(Job(
                    source="linkedin",
                    title=t.get_text(strip=True),
                    company=c.get_text(strip=True) if c else "",
                    url=link,
                    location="Remote",
                    posted=parse_dt(tm.get("datetime") if tm else None),
                ))
            time.sleep(PAUSE)
    return jobs
