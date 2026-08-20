# Vendored skills

Third-party skills vendored into this repo.

## Source

Both skills, and the [`service/`](../../service) directory they depend on, come
from [`watermarks-remover`](https://github.com/guillaumemeyer/watermarks-remover)
(MIT, see `LICENSE`), imported from the `main` branch tarball at v0.5.0.
`service/` is copied as-is minus `__pycache__`.

### Local modifications

Everything is upstream's except the following. Re-apply these after any re-sync,
or drop them if upstream adopts equivalent wording.

- `clean-user-facing-text/SKILL.md` — the `description` was written for Cursor
  and named it twice. Changed `Use in Cursor when the user asks` to `Use when
  the user asks`, and `when an installed Cursor Rule explicitly requires this
  workflow` to `when a project convention explicitly requires this workflow`.
  Trigger wording only; the workflow body is untouched.

## `clean-user-facing-text/`

Self-contained. Ships four Python scripts (stdlib only, Python 3.10+) under
`scripts/` that strip invisible/format Unicode — zero-width characters, word
joiners, bidi controls, tag characters — from prose you own.

```bash
python3 .claude/skills/clean-user-facing-text/scripts/inspect_text.py --json FILE
python3 .claude/skills/clean-user-facing-text/scripts/clean_text.py FILE -o OUT --stats --no-normalize-spaces
```

`inspect_text.py` exits `1` when it finds hits and `0` when clean, so it works
as a CI check. `--no-normalize-spaces` (recommended default) preserves NBSP and
other layout-bearing spaces.

## `remove-ai-marks/`

This skill ships no code — it is a thin HTTP client that POSTs to the
`watermarks-remover` service, vendored at [`service/`](../../service) in this
repo. Start it before using the skill:

```bash
python3 service/scripts/server.py --host 127.0.0.1 --port 8765
```

The skill reads `$WATERMARKS_SERVICE_URL`, defaulting to
`http://127.0.0.1:8765`, so no configuration is needed for a local run. Check
it with `curl -sf http://127.0.0.1:8765/health`. With the service down, the
skill only reports the endpoint unreachable.

Bind to loopback unless you set `WATERMARKS_SERVER_API_KEY` — the server warns
about this on startup.

### What works without extra tooling

The core service is Python 3.10+ **stdlib only** and adds no dependency to
`requirements.txt`. Out of the box it handles text Layer A (invisible Unicode),
container metadata (Markdown, HTML, DOCX/XLSX/PPTX, EPUB, ODT, SVG), and image
metadata. `GET /capabilities` reports the rest, and on a bare checkout it is
all `false`:

| Absent | Consequence |
| --- | --- |
| `exiftool`, `qpdf` | PDF strip is degraded — best-effort without exiftool, incomplete without qpdf |
| `c2patool` | C2PA manifests cannot be inspected |
| `ctrlregen`, `diffusion` | No pixel-domain removal; image cleaning is metadata-only |
| `markllm`, `gumbel`, `claude-text`, `synthid` | No watermark detection, so no before/after measurement |

The optional `Dockerfile.*` files and `setup_*.sh` scripts under `service/`
build those heavy backends. They need external checkouts and are not required
for anything above.

## Scope note

These tools strip AI provenance signals — C2PA/Content Credentials, EXIF/XMP,
and statistical text watermarks. That has legitimate uses (metadata privacy,
publishing hygiene, watermark-robustness research) and illegitimate ones.
Both skills carry upstream guidance on the line between them; see
`remove-ai-marks/references/ethics.md` and
`clean-user-facing-text/references/responsible-use.md`.
