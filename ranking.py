"""Puntúa cada oferta según el perfil. Score alto = abrir primero."""
from __future__ import annotations
import re
from datetime import datetime, timezone
from sources.base import Job

# Regiones/países que NO son LatAm: si el aviso apunta a esa zona/idioma local,
# se descarta (no aplican para alguien LatAm/Argentina remoto).
# (LatAm queda permitido: Argentina, México, Brasil, Colombia, español, etc.)
REGIONS_BLOCK = [
    # África
    "west africa", "east africa", "north africa", "sub-saharan", "africa",
    "nigeria", "kenya", "ghana", "south africa", "ethiopia", "tanzania", "uganda",
    # Asia
    "thailand", "vietnam", "indonesia", "philippines", "malaysia", "singapore",
    "india", "pakistan", "bangladesh", "sri lanka", "nepal",
    "china", "korea", "japan", "hong kong", "taiwan", "mongolia", "cambodia", "myanmar",
    "apac", "southeast asia", "south asia", "east asia",
    # MENA / Medio Oriente
    "mena", "middle east", "uae", "dubai", "abu dhabi", "saudi", "qatar",
    "kuwait", "bahrain", "oman", "egypt", "israel", "jordan", "lebanon", "iran", "iraq",
    # Europa / CIS
    "germany", "france", "italy", "spain", "poland", "netherlands", "belgium",
    "united kingdom", "ireland", "nordic", "scandinavia", "switzerland", "austria",
    "russia", "ukraine", "turkey", "türkiye", "greece", "romania", "czech", "balkan",
    "emea",
    # Idiomas locales (señal de comunidad regional no hispana)
    "vietnamese", "turkish", "korean", "japanese", "chinese", "mandarin", "cantonese",
    "thai", "hindi", "german", "french-speaking", "russian-speaking", "arabic",
    "indonesian", "filipino", "tagalog", "polish", "italian-speaking",
    # Norteamérica con requisito de presencia local (opcional, suelen pedir US work auth)
    "u.s. based", "us-based", "usa only",
]


def _region_blocked(title: str, location: str) -> str | None:
    hay = f"{title} {location}".lower()
    for region in REGIONS_BLOCK:
        # match por palabra completa para evitar falsos positivos
        if re.search(r"(?<![a-z])" + re.escape(region) + r"(?![a-z])", hay):
            return region
    return None


def _not_remote(title: str, location: str) -> bool:
    """True si el aviso es híbrido/presencial y NO es en Buenos Aires."""
    hay = f"{title} {location}".lower()
    if "buenos aires" in hay or "argentina" in hay:
        return False                          # en BA, hí­brido/presencial OK
    return bool(re.search(r"hybrid|on-?site|on site|in-office|in office|presencial", hay))


def score(job: Job, profile: dict) -> tuple[float, str | None]:
    """Devuelve (score, motivo_descarte). Si motivo != None, se descarta."""
    text = job.haystack
    title = job.title.lower()

    # ── descartes duros ──
    for bad in profile.get("keywords_bad", []):
        if bad.lower() in title:                 # en el título es fatal
            return 0.0, f"título contiene '{bad}'"
    region = _region_blocked(title, "")          # solo título (la ubicación es la HQ)
    if region:
        return 0.0, f"región no-LatAm: {region}"
    if _not_remote(title, job.location):
        return 0.0, "híbrido/presencial fuera de BA"
    if not job.title or not job.url:
        return 0.0, "incompleto"

    pts = 0.0

    # ── match de título (lo que más pesa) ──
    titles = profile.get("titles", [])
    for i, t in enumerate(titles):
        if t.lower() in title:
            pts += 50 - i * 5                    # más arriba en la lista = más peso
            break

    # ── keywords buenas ──
    for kw in profile.get("keywords_good", []):
        if kw.lower() in text:
            pts += 4

    # ── keywords malas en el cuerpo (penaliza, no descarta) ──
    for bad in profile.get("keywords_bad", []):
        if bad.lower() in text:
            pts -= 6

    # ── remoto ──
    if "remote" in text or job.location.lower() in ("remote", "worldwide", ""):
        pts += 8

    # ── frescura: ofertas nuevas arriba ──
    if job.posted:
        age_days = (datetime.now(timezone.utc) - job.posted).days
        if age_days <= 1:
            pts += 12
        elif age_days <= 3:
            pts += 7
        elif age_days <= 7:
            pts += 3

    # ── salario visible (señal de oferta seria) ──
    if job.salary:
        pts += 5

    return pts, None
