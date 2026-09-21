# SDOC Hackathon — Shipping Document Verification

Pipeline that reads a shipping-ops email inbox, classifies each message
(`BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, `SPAM`), and for
document-comparison requests, extracts 7 shipment fields from the Shipping
Instruction (SI) and draft Bill of Lading (BL) attachments, compares them,
and reports the outcome — escalating to a human (`NEEDS_REVIEW`) instead of
guessing when it can't confidently decide.

Fully rule-based / deterministic — no LLM, no paid API, no network calls.

**Score against the organizers' ground truth: 0.987** (Stage-1 classification
100% accuracy, defect precision 1.0 / recall 0.978, reliability escalation
recall 1.0). See [Known limitations](#known-limitations) for the 3 emails
that don't match exactly and why.

## AI & Cloud

- **AI Integration**: built end-to-end using [Claude Code](https://claude.com/claude-code),
  Anthropic's AI coding agent, as the core development tool. Every module
  (`classify.py`, `extract.py`, `synonyms.py`, `compare.py`, `pipeline.py`),
  the 40-test suite (validated against the real dataset throughout, not
  written after the fact), the JavaScript port of the pipeline powering the
  live demo, and this documentation were designed, implemented, debugged,
  and iterated end-to-end through an AI-assisted engineering workflow. The
  runtime pipeline itself is deliberately rule-based (see below) — the AI
  integration here is in how the system was *built*.
- **Cloud Infrastructure**: hosted and deployed on GitHub (cloud-hosted git)
  and served via [GitHub Pages](https://iban-1.github.io/AverisXHackathon/)
  (GitHub's cloud hosting/CDN) — the live prototype is publicly accessible
  with no local server required.

## Approach

1. **Classify** (`src/sdoc/classify.py`) — regex/keyword rules on the
   *subject line only* (body text is intentionally excluded here: a
   legitimate request's body often lists unrelated words like "3 Original
   invoice" as a required document, which would otherwise cause false
   category matches). Subject lines in this inbox are deterministically
   coded (`TO CONFIRM DOCS`, `SI - ... - DIRECT(...)`, `RAK BILLING ...
   MISSING GR`, etc.) — see `data/README.md`'s per-category signal list.
2. **Extract** (`src/sdoc/extract.py`, `synonyms.py`) — a label → canonical
   field dictionary handles the "same information, different label"
   problem (`Port of Loading` = `Load Port` = `POL`). One dictionary drives
   extraction across all 4 attachment formats:
   - `.txt` / PDF text: `Label: value` or PDF's columnar `Label   value`
     (no colon) layout.
   - `.docx`: 2-column table `[label cell, value cell]`.
   - `.xlsx`: 2-column rows; multi-part values are `|`-joined.
3. **Compare** (`compare.py`) — normalizes values (case/whitespace for
   names & ports, numeric parsing for container count & weight) and diffs
   the 7 fields. A field missing on *either* side is never treated as a
   mismatch — the whole comparison escalates instead (see below).
4. **Escalate** (`pipeline.py`) — routes to `NEEDS_REVIEW` with the right
   `review_reason` instead of guessing:
   - `missing_attachment` — a comparison request with 0/1 attachments where
     the body explicitly says "compare... " despite that (distinguishing it
     from the ~45% of ordinary "please send the draft BL" requests, which
     correctly stay `OK`/no-defect since there's nothing to compare yet).
   - `wrong_doc_type` — the "BL"/"SI" attachment's own header line doesn't
     say `SHIPPING INSTRUCTION` / `BILL OF LADING` (it's actually a
     Commercial Invoice, Packing List, or Certificate of Origin).
   - `unreadable` — the file won't open (garbled/truncated), or extraction
     comes back completely empty (e.g. an image-only scanned PDF with no
     text layer — would need OCR, out of scope here, see below).
   - `missing_value` — a field is blank/placeholder (`???`, `_______`,
     `N/A`, `TBA`, `NIL`, `PENDING`) on either document.

## Layout

- `data/` — participant dataset (inbox, attachments, `sample_submission.json`,
  organizers' `loader.py`). No ground truth included.
- `organizer/` — local scoring server + the answer key, used only to
  self-score submissions. Not committed (see `.gitignore`), never read
  directly by the pipeline itself — only `organizer/server/score_cli.py`
  touches it, and only to grade a finished `submission.json`.
- `src/sdoc/` — pipeline source (`classify.py`, `extract.py`, `synonyms.py`,
  `compare.py`, `pipeline.py`).
- `tests/` — pytest suite (40 tests), run against the real dataset
  throughout, not just synthetic fixtures.
- `submission.json` — generated output (gitignored; regenerate with the
  command below).

## Running

```bash
pip install -r requirements.txt
python -m sdoc.pipeline --data data --out submission.json
```

(`PYTHONPATH=src` if running outside an installed package — the repo has no
`setup.py`/`pyproject.toml` yet, so run either with `PYTHONPATH=src python -m
sdoc.pipeline ...` or `cd src && python -m sdoc.pipeline --data ../data`.)

## Tests

```bash
python -m pytest tests/ -q
```

## Scoring

No Docker needed — `score_cli.py` runs standalone against the organizers'
private `ground_truth.json`:

```bash
cd organizer/server
python score_cli.py ../../submission.json --json
```

(`docker compose up --build` in `organizer/` also works and adds an HTTP
`/submit` endpoint, but isn't required.)

## Known limitations

- **3 emails don't match ground truth exactly** (email_208, 351, 407): all
  three have a PDF whose *own text layer* is corrupted — the long label
  "Notify Party/Intermediate Consignee" visually overlaps its value in the
  source PDF, so pdfplumber extracts garbage (e.g. `Notify
  Party/Intermediate ConsNigAnGeAePPA EXPORTS`). The pipeline detects this
  corruption (the "value" contains leftover label vocabulary) and
  deliberately leaves the field unextracted rather than reporting a
  scrambled name as real data — which routes the whole comparison to
  `NEEDS_REVIEW/missing_value` instead of matching gold's `OK` or
  `MISMATCH` outcome for those 3. This is the intended trade-off of
  "escalate when uncertain instead of guessing," and it's the only
  remaining source of error in the whole 520-email set.
- **No OCR** — the dataset's only image-only/scanned PDFs are 3 of the 20
  deliberately-built reliability edge cases, whose ground truth is fixed as
  `NEEDS_REVIEW/unreadable` regardless of OCR capability (they exist to
  test escalation, not to be solved). All 20 edge cases are already
  correctly handled without OCR (escalation recall = 1.0), so it wouldn't
  change the score on this dataset. `src/sdoc/extract.py`'s per-format
  dispatch (`extract_fields`) is structured so a Tesseract-based
  `extract_fields_scanned_pdf` could be added as another branch if needed
  for other data.
- **No LLM/paid API at runtime** — by design (see project history). Every
  capability (label-synonym matching, category classification, doc-type
  detection) is rule-based. AI was used to *build* the system (see
  [AI & Cloud](#ai--cloud) above), not to run it — this was a deliberate
  cost/reliability choice, not a gap.
