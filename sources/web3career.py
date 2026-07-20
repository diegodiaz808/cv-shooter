"""web3.career — usa JSON-LD (JobPosting) + links de la tabla."""
from __future__ import annotations
import json
from bs4 import BeautifulSoup
from .base import Job, get, parse_dt

BASE = "https://web3.career"


def _slug(term: str) -> str:
    return term.strip().lower().replace(" ", "-")


def fetch(profile: dict) -> list[Job]:
    jobs: list[Job] = []
    seen: set[str] = set()
    # una búsqueda por cada título ideal, remoto
    for term in profile.get("titles", []):
        url = f"{BASE}/{_slug(term)}-jobs"
        try:
            r = get(url)
            if r.status_code != 200:
                continue
        except Exception:
            continue
        soup = BeautifulSoup(r.text, "lxml")

        # metadatos de JSON-LD, en orden (coincide con el orden de las filas)
        ld = []
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                obj = json.loads(tag.string or "")
            except Exception:
                continue
            for it in (obj if isinstance(obj, list) else [obj]):
                if isinstance(it, dict) and it.get("@type") == "JobPosting":
                    ld.append(it)

        # filas de la tabla: título (anchor text) + link
        for i, tr in enumerate(soup.select("tr[data-jobid]")):
            a = tr.select_one('a[href^="/"]')
            if not a:
                continue
            title = a.get_text(strip=True)
            link = BASE + a["href"]
            if not title or link in seen:
                continue
            seen.add(link)
            meta = ld[i] if i < len(ld) else {}
            org = (meta.get("hiringOrganization") or {}).get("name", "")
            if not org:                       # fallback: empresa del slug
                slug = a["href"].rstrip("/").rsplit("/", 1)[0]
                org = slug.rsplit("-", 1)[-1].replace("-", " ").title()
            jobs.append(Job(
                source="web3.career",
                title=title,
                company=org,
                url=link,
                posted=parse_dt(meta.get("datePosted")),
                description=(meta.get("description") or "")[:600],
            ))
    return jobs
