# Vendored skills

Third-party skills vendored into this repo.

## Source

Both skills come from [`watermarks-remover`](https://github.com/guillaumemeyer/watermarks-remover)
(MIT, see `LICENSE`), imported from the `main` branch tarball at v0.5.0.

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

**Requires a companion service that is not vendored here.** This skill ships no
code — it is a thin HTTP client that POSTs to the `watermarks-remover` service
(the upstream repo's `service/` directory) at `$WATERMARKS_SERVICE_URL`,
default `http://127.0.0.1:8765`. Without that service running, the skill does
nothing but report the endpoint is unreachable.

To use it, run the service from a checkout of the upstream repo (`make serve`)
or its published container image.

## Scope note

These tools strip AI provenance signals — C2PA/Content Credentials, EXIF/XMP,
and statistical text watermarks. That has legitimate uses (metadata privacy,
publishing hygiene, watermark-robustness research) and illegitimate ones.
Both skills carry upstream guidance on the line between them; see
`remove-ai-marks/references/ethics.md` and
`clean-user-facing-text/references/responsible-use.md`.
