"""remoteok.com — API JSON pública (tag crypto)."""
from __future__ import annotations
from .base import Job, get, parse_dt

API = "https://remoteok.com/api?tags=crypto"


def fetch(profile: dict) -> list[Job]:
    try:
        r = get(API)
        data = r.json()
    except Exception:
        return []

    terms = [t.lower() for t in profile.get("titles", []) + profile.get("keywords_good", [])]
    jobs: list[Job] = []
    for j in data:
        if not isinstance(j, dict) or not j.get("position"):
            continue
        tags = [t for t in (j.get("tags") or []) if isinstance(t, str)]
        blob = f"{j.get('position','')} {' '.join(tags)} {j.get('description','')}".lower()
        if terms and not any(t in blob for t in terms):
            continue                          # descarta lo que no roza tu perfil
        slug = j.get("slug") or j.get("id")
        url = j.get("apply_url") or f"https://remoteok.com/remote-jobs/{slug}"
        jobs.append(Job(
            source="remoteok",
            title=j.get("position", "").strip(),
            company=(j.get("company") or "").strip(),
            url=url,
            location=j.get("location") or "Remote",
            salary=(f"${j.get('salary_min'):,}+" if j.get("salary_min") else ""),
            tags=tags,
            posted=parse_dt(j.get("date") or j.get("epoch")),
            description=(j.get("description") or "")[:500],
        ))
    return jobs
