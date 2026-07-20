# CV-Shooter

Job-hunting bot: scrapes crypto job boards + LinkedIn, ranks every offer against your profile, filters out what you've already seen, and opens the best ones as tabs in a dedicated Chrome window. One command, zero repeated listings.

> Docs in Spanish: [README.es.md](README.es.md)

## How it works

1. **Gather** — pluggable source registry (web3.career, CryptoJobsList, Remote3, RemoteOK, LinkedIn). Each source module implements `fetch(profile)`.
2. **Rank** — every job is scored against the profile: title matches (weighted), good/bad keywords, seniority, recency. Hard rejects are dropped.
3. **Filter smart** — LinkedIn candidates are *lazily enriched* (detail page fetched only for jobs that might make the cut) to verify remote / Easy Apply constraints without hammering the site.
4. **Dedupe forever** — a persistent `seen.json` guarantees a job is only ever shown once; an append-only JSONL log keeps history.
5. **Open** — AppleScript opens one fresh Chrome window per profile with the winners as tabs.

Multiple profiles supported (e.g. one for community roles, one for product design), each with its own CV, sources and scoring.

## Usage

```bash
cp config.example.yaml config.yaml   # fill in your profile
./apply              # run everything
./apply --dry        # list in terminal only, don't open windows
./apply --reset-seen # forget history
```

## Stack

Python · YAML config · pluggable scrapers · AppleScript/Chrome automation
