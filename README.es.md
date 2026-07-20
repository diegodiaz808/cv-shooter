# cv-apply

Busca ofertas en boards de crypto, las rankea según tu perfil y abre las
mejores en pestañas de Chrome. Recuerda lo que ya te mostró para no repetir.

## Uso

```bash
cd ~/cv-apply
./apply               # busca los 2 perfiles y abre 1 ventana de Chrome por cada uno
./apply --dry         # solo lista en la terminal, no abre nada
./apply --reset-seen  # olvida el historial (vuelve a mostrar todo)
```

Un solo comando hace todo el proceso: busca para cada perfil de `run:` en el
config, y abre los resultados de cada uno en **su propia ventana** de Chrome
(main hasta 25 pestañas, product hasta 10). Termina. Lo mostrado queda
registrado y no vuelve a aparecer.

La primera vez macOS pide permiso para que la terminal controle Chrome
(Automatización) — aceptá una vez.

## Configurar

Todo se edita en **`config.yaml`**:
- `profiles`: keywords, títulos y filtros por perfil. El ranking usa esto.
- `settings.max_tabs` / `recent_days`: cuántas abrir y antigüedad máxima.
- `settings.active_profile`: perfil por defecto.
- `sources`: prendé/apagá fuentes con `enabled`.

## Cómo rankea

`ranking.py` puntúa cada oferta: match de título (lo que más pesa) + keywords
buenas + remoto + frescura + salario visible; descarta por keywords malas en el
título. Más score = se abre primero.

## Fuentes

Cada perfil define sus propias fuentes con `sources:` en `config.yaml`
(perfil `main` = boards de crypto; perfil `product` = solo LinkedIn).

| fuente | estado | método |
|---|---|---|
| web3.career | ✅ | tabla + JSON-LD |
| cryptojobslist | ✅ | `__NEXT_DATA__` |
| linkedin | ✅ | endpoint guest (sin login) |
| remote3 | ⚠️ parcial | RSS (solo recientes) |
| laborx | ⛔ pendiente | JS-heavy |
| beincrypto | ⛔ pendiente | — |

Agregar una fuente = un archivo en `sources/` con `fetch(profile) -> list[Job]`
y registrarla en `sources/__init__.py` + `config.yaml`.

## Datos

- `data/seen.json`: ofertas ya mostradas (anti-duplicado).
- `data/applied_log.jsonl`: histórico de todo lo abierto, con fecha y score.

## Pendiente / roadmap

1. Sumar fuentes: laborx, beincrypto, y las que uses.
2. Perfil B (Product & Design) — copiar bloque en `config.yaml`.
3. Autocompletado de formularios con datos de `identity`.
4. LinkedIn "Easy Apply" automático (al final, con cuidado de baneo).
5. CV adaptado por oferta.
