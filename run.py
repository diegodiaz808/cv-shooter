#!/usr/bin/env python3
"""
CV-APPLY — proceso único: busca para cada perfil del config y abre los
resultados de cada uno en SU PROPIA ventana de Chrome. Después termina.

    ./apply              # corre todo (lo normal)
    ./apply --dry        # solo lista en la terminal, no abre ventanas
    ./apply --reset-seen # olvida el historial antes de correr
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from sources import REGISTRY, linkedin
from ranking import score

ROOT = Path(__file__).parent
SEEN_FILE = ROOT / "data" / "seen.json"
LOG_FILE = ROOT / "data" / "applied_log.jsonl"


# ─────────────── datos ───────────────
def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def load_seen() -> dict:
    return json.loads(SEEN_FILE.read_text()) if SEEN_FILE.exists() else {}


def save_seen(seen: dict):
    SEEN_FILE.write_text(json.dumps(seen, indent=1))


# ─────────────── pipeline ───────────────
def sources_for(cfg, profile):
    if profile.get("sources"):
        return profile["sources"]
    return [s["name"] for s in cfg["sources"] if s.get("enabled")]


def gather(sources, profile):
    jobs = []
    for name in sources:
        mod = REGISTRY.get(name)
        if not mod:
            print(f"  ⚠ fuente desconocida: {name}")
            continue
        try:
            found = mod.fetch(profile)
            print(f"    {name:16} {len(found)} ofertas")
            jobs.extend(found)
        except Exception as e:
            print(f"    ⚠ {name} falló: {e}")
    return jobs


def rank(jobs, profile, recent_days):
    by_uid = {}
    for j in jobs:
        by_uid.setdefault(j.uid, j)
    jobs = list(by_uid.values())
    now = datetime.now(timezone.utc)
    jobs = [j for j in jobs
            if j.posted is None or (now - j.posted).days <= recent_days]
    scored = []
    for j in jobs:
        pts, reject = score(j, profile)
        if reject is None and pts > 0:
            scored.append((pts, j))
    scored.sort(key=lambda x: x[0], reverse=True)
    return jobs, scored


def _passes_easy_apply(job, profile):
    """Regla: solo Easy Apply, salvo puestos junior/mid (más oportunidad)."""
    jr_mid = [s.lower() for s in profile.get("junior_mid_levels", [])]
    if job.seniority and job.seniority in jr_mid:
        return True
    return job.easy_apply is True


def _passes_remote(job):
    """Descarta híbrido/presencial, salvo Buenos Aires/Argentina."""
    loc = f"{job.title} {job.location}".lower()
    if "buenos aires" in loc or "argentina" in loc:
        return True
    return job.workplace not in ("on-site", "hybrid")


def select_linkedin(fresh, profile, limit):
    """Enriquece candidatas de LinkedIn en orden de ranking y filtra
    (remoto y/o Easy Apply) hasta llenar el cupo. Solo pega al detalle de
    las necesarias, no de todas."""
    need_remote = profile.get("remote_only")
    need_easy = profile.get("only_easy_apply")
    picks = []
    for p, j in fresh:
        if len(picks) >= limit:
            break
        if j.source == "linkedin" and (need_remote or need_easy):
            linkedin.enrich(j)
            if need_remote and not _passes_remote(j):
                continue
            if need_easy and not _passes_easy_apply(j, profile):
                continue
        picks.append((p, j))
    return picks


def search(cfg, pname, limit):
    """Busca y devuelve (picks_a_abrir, nuevas_total)."""
    profile = cfg["profiles"][pname]
    recent_days = cfg["settings"].get("recent_days", 7)
    srcs = sources_for(cfg, profile)
    print(f"\n▶ {profile.get('label', pname)}  ({', '.join(srcs)})")
    jobs = gather(srcs, profile)
    all_jobs, scored = rank(jobs, profile, recent_days)
    seen = load_seen()
    fresh = [(p, j) for p, j in scored if j.uid not in seen]

    n_match = len(scored)            # ofertas que matchean tu perfil
    n_new = len(fresh)               # de esas, las que nunca te mostré

    needs_enrich = profile.get("only_easy_apply") or profile.get("remote_only")
    if needs_enrich:
        crit = []
        if profile.get("remote_only"): crit.append("remoto")
        if profile.get("only_easy_apply"): crit.append("Easy Apply/junior-mid")
        print(f"    → {n_match} matchean · {n_new} nuevas · "
              f"verificando detalle ({', '.join(crit)})…")
        picks = select_linkedin(fresh, profile, limit)
    else:
        picks = fresh[:limit]

    n_open = len(picks)
    if n_new == 0:
        print(f"    → {n_match} matchean · 0 nuevas — ya las viste todas. Nada para abrir.")
    elif needs_enrich:
        print(f"    → abro {n_open} (verificadas) · resto sigue en cola")
    else:
        print(f"    → {n_match} matchean · {n_new} nuevas · "
              f"abro {n_open} (tope {limit}) · quedan {n_new - n_open} para la próxima")
    return picks, n_new


def print_list(picks):
    for i, (p, j) in enumerate(picks, 1):
        sal = f"  💰{j.salary}" if j.salary else ""
        print(f"      {i:>2}. [{p:>3.0f}] {j.title[:44]} — {j.company[:20]}{sal}")


# ─────────────── abrir en ventana propia ───────────────
def open_window(urls, browser):
    """Abre una ventana NUEVA de Chrome con todas las URLs como pestañas."""
    if not urls:
        return
    js_list = ",".join('"%s"' % u.replace('"', '%22') for u in urls)
    script = f'''
    tell application "{browser}"
        activate
        set theURLs to {{{js_list}}}
        make new window
        set i to 0
        repeat with u in theURLs
            set i to i + 1
            if i = 1 then
                set URL of active tab of front window to u
            else
                tell front window to make new tab with properties {{URL:u}}
            end if
        end repeat
    end tell
    '''
    subprocess.run(["osascript", "-e", script], check=False)


def register(picks, seen, when):
    with open(LOG_FILE, "a") as log:
        for p, j in picks:
            seen[j.uid] = {"title": j.title, "company": j.company, "url": j.url,
                           "source": j.source, "shown_at": when, "score": round(p, 1)}
            log.write(json.dumps(seen[j.uid], ensure_ascii=False) + "\n")
    save_seen(seen)


# ─────────────── main ───────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="no abre ventanas")
    ap.add_argument("--reset-seen", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    if args.reset_seen:
        SEEN_FILE.unlink(missing_ok=True)
        print("Historial borrado.")

    browser = cfg["settings"].get("browser", "Google Chrome")
    when = datetime.now(timezone.utc).isoformat()
    seen = load_seen()
    total = 0

    print("═══════════════════════════════════════════")
    print("  CV-APPLY")
    print("═══════════════════════════════════════════")

    resumen = []
    for entry in cfg.get("run", []):
        pname = entry["profile"]
        limit = entry.get("max_tabs", 20)
        picks, n_new = search(cfg, pname, limit)
        label = cfg["profiles"][pname].get("label", pname)
        if not picks:
            resumen.append(f"  {label}: 0 nuevas — nada para abrir")
            continue
        print_list(picks)
        if not args.dry:
            open_window([j.url for _, j in picks], browser)
            register(picks, seen, when)
            total += len(picks)
        resumen.append(f"  {label}: {n_new} nuevas · "
                       f"{'(dry) ' if args.dry else ''}abiertas {len(picks)} · "
                       f"quedan {n_new - len(picks)}")

    print("\n───────────────────────────────────────────")
    print("RESUMEN")
    for line in resumen:
        print(line)
    if args.dry:
        print("\n(--dry: no se abrió nada ni se guardó historial)")
    elif total:
        print(f"\n✓ {total} pestañas abiertas en ventanas separadas. "
              f"Lo abierto no se vuelve a mostrar; lo que quedó sale la próxima.")
    else:
        print("\n✓ No había nada nuevo. Ya viste todo lo disponible por ahora.")


if __name__ == "__main__":
    sys.exit(main())
