# SDOC Hackathon — Shipping Document Verification

Pipeline that reads a shipping-ops email inbox, classifies each message
(`BL_COMPARISON`, `SI_REQUEST`, `INVOICE_QUERY`, `GENERAL`, `SPAM`), and for
document-comparison requests, extracts 7 shipment fields from the Shipping
Instruction (SI) and draft Bill of Lading (BL) attachments, compares them,
and reports the outcome — escalating to a human (`NEEDS_REVIEW`) instead of
guessing when it can't confidently decide.

Fully rule-based / deterministic. No paid API required.

## Layout

- `data/` — participant dataset (inbox, attachments, `sample_submission.json`,
  organizers' `loader.py`). No ground truth included.
- `organizer/` — local scoring server (Docker) + the answer key, used only to
  self-score submissions. Not committed (see `.gitignore`), never read
  directly by the pipeline.
- `src/sdoc/` — pipeline source.
- `submission.json` — generated output, scored against `organizer/`'s
  `/submit` endpoint or `score_cli.py`.

## Running

TBD as milestones land — see the running plan for the build order.

## Scoring

```bash
cd organizer && docker compose up --build   # serves http://localhost:8080
# then, from the project root:
python -c "from data.loader import Inbox; import json; \
  ib = Inbox('http://localhost:8080'); \
  print(ib.submit(json.load(open('submission.json')))['final_score'])"
```
