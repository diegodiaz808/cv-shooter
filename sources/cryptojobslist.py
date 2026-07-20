"""cryptojobslist.com — usa el blob __NEXT_DATA__ (Next.js)."""
from __future__ import annotations
import json
import re
from .base import Job, get, parse_dt

BASE = "https://cryptojobslist.com"
_NEXT = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def _slug(term: str) -> str:
    return term.strip().lower().replace(" ", "-")


def fetch(profile: dict) -> list[Job]:
    jobs: list[Job] = []
    seen: set[str] = set()
    for term in profile.get("titles", []):
        url = f"{BASE}/{_slug(term)}"
        try:
            r = get(url)
            m = _NEXT.search(r.text)
            if not m:
                continue
            data = json.loads(m.group(1))
        except Exception:
            continue
        for j in data.get("props", {}).get("pageProps", {}).get("jobs", []) or []:
            slug = j.get("seoSlug")
            if not slug:
                continue
            link = f"{BASE}/jobs/{slug}"
            if link in seen:
                continue
            seen.add(link)
            jobs.append(Job(
                source="cryptojobslist",
                title=(j.get("jobTitle") or "").strip(),
                company=(j.get("companyName") or "").strip(),
                url=link,
                location=j.get("jobLocation") or ("Remote" if j.get("remote") else ""),
                salary=j.get("salaryString") or "",
                tags=[t for t in (j.get("tags") or []) if isinstance(t, str)],
                posted=parse_dt(j.get("publishedAt") or j.get("createdAt")),
            ))
    return jobs
