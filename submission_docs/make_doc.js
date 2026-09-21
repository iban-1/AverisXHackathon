const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, convertInchesToTwip,
} = require("docx");

const US_LETTER = { width: 12240, height: 15840 };

const numbering = {
  config: [
    {
      reference: "bullets",
      levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: convertInchesToTwip(0.35), hanging: convertInchesToTwip(0.2) } } } },
      ],
    },
  ],
};

const ACCENT = "1E5F74"; // deep harbor teal — matches the live demo's accent
const DARK = "1D2430";   // navy-charcoal ink
const GREY = "5B6478";

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 160 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 4 } },
    children: [new TextRun({ text, bold: true, color: ACCENT, size: 30 })],
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 100 },
    children: [new TextRun({ text, bold: true, color: DARK, size: 24 })],
  });
}

function p(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 140 },
    children: [new TextRun({ text, size: 22, color: DARK, ...opts })],
  });
}

function bullet(text, opts = {}) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text, size: 22, color: DARK, ...opts })],
  });
}

function boldLabel(label, rest) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80 },
    children: [
      new TextRun({ text: label, bold: true, size: 22, color: DARK }),
      new TextRun({ text: rest, size: 22, color: DARK }),
    ],
  });
}

function statCell(value, label) {
  return new TableCell({
    width: { size: 2340, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: "E4EEF0" },
    margins: { top: 160, bottom: 160, left: 120, right: 120 },
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 40 },
        children: [new TextRun({ text: value, bold: true, size: 30, color: ACCENT })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: label, size: 18, color: GREY })],
      }),
    ],
  });
}

const doc = new Document({
  numbering,
  sections: [
    {
      properties: { page: { size: US_LETTER, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
      children: [
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 40 },
          children: [new TextRun({ text: "Shipping Document Verification", bold: true, size: 44, color: ACCENT })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 60 },
          children: [new TextRun({ text: "SDOC Pipeline — Averis Hackathon 2026", size: 26, color: DARK })],
        }),
        new Paragraph({
          alignment: AlignmentType.CENTER,
          spacing: { after: 300 },
          children: [new TextRun({ text: "Team Elevate", size: 22, color: GREY, italics: true })],
        }),

        h1("Project Description"),
        p("Purpose: An automated pipeline that triages a shipping operations team's inbox and catches discrepancies between Shipping Instructions (SI) and draft Bills of Lading (BL) before they become costly errors — replacing a slow, error-prone manual process with a deterministic, auditable system."),
        p("Problem Statement: Shipping operations teams receive a mixed inbox of document-comparison requests, new SI requests, invoice queries, general updates, and spam — all requiring manual triage. For comparison requests, staff must manually cross-check 7 critical fields (shipper, consignee, notify party, ports, container count, gross weight) across two documents that often use inconsistent field labels for the same data (“Port of Loading” vs “Load Port”), making mismatches easy to miss and corrections costly."),
        p("Solution: A fully rule-based pipeline that (1) classifies every inbox email into 5 categories from its coded subject line, (2) extracts the 7 shipment fields from SI/BL attachments across 4 formats (TXT, PDF, DOCX, XLSX) using a label-synonym dictionary that resolves naming inconsistencies, (3) compares values with format-aware normalization, and (4) escalates to human review — with a specific reason — whenever it cannot confidently decide, rather than guessing."),
        p("GitHub: https://github.com/iban-1/AverisXHackathon", { color: GREY }),

        h1("AI & Cloud Integration"),
        boldLabel("AI Integration: ", "this solution was built end-to-end using Claude Code, Anthropic's AI coding agent, as the core development tool — not a peripheral aid. Every module (classify.py, extract.py, synonyms.py, compare.py, pipeline.py), the 40-test suite validated against the real dataset, the JavaScript port of the pipeline powering the live demo, and this documentation were designed, implemented, debugged, and iterated end-to-end through an AI-assisted engineering workflow."),
        boldLabel("Cloud Infrastructure: ", "the project is hosted and deployed on cloud infrastructure throughout — source control on GitHub (cloud-hosted git), and the live prototype served via GitHub Pages (GitHub's cloud hosting/CDN) at https://iban-1.github.io/AverisXHackathon/, publicly accessible with no local server required."),

        h1("Results"),
        new Table({
          columnWidths: [2340, 2340, 2340, 2340],
          width: { size: 9360, type: WidthType.DXA },
          rows: [
            new TableRow({ children: [statCell("0.987", "Final Score"), statCell("100%", "Stage-1 Accuracy"), statCell("1.0", "Defect Precision"), statCell("100%", "Escalation Recall")] }),
          ],
        }),
        new Paragraph({ spacing: { before: 160, after: 0 }, children: [] }),
        p("Scored against the organizers' hidden ground truth across all 520 emails. Only 3 emails deviate from ground truth — all the same known, deliberate “escalate over guess” trade-off on PDFs whose own text layer is corrupted (see Challenges Faced).", { color: GREY, italics: true }),

        h1("Technical Architecture"),
        bullet("Four-stage pipeline: Classify → Extract → Compare → Escalate, each stage an independent, testable module (classify.py, extract.py, compare.py, pipeline.py)."),
        bullet("Fully rule-based / deterministic — no LLM, no external API, no network dependency, zero inference cost."),
        bullet("A single label-synonym dictionary (synonyms.py) drives extraction consistently across all four attachment formats."),
        bullet("40-test pytest suite run against the real dataset throughout development, not just synthetic fixtures."),

        h1("Implementation Details"),
        boldLabel("Classify: ", "regex/keyword rules on subject lines only — deterministically coded in this domain. Body text is intentionally excluded, since routine phrases like “3 Original invoice” in a document checklist would otherwise cause false category matches."),
        boldLabel("Extract: ", "one canonical field dictionary resolves label synonyms (“Port of Loading” = “Load Port” = “POL”) across TXT, PDF (columnar text layout), DOCX (table cells), and XLSX (pipe-joined multi-part values)."),
        boldLabel("Compare: ", "normalizes case/whitespace for names and ports, parses numerics for container count and gross weight. A field missing on either side never becomes a false mismatch — it escalates instead."),
        boldLabel("Escalate: ", "four distinct reliability reasons (missing_attachment, wrong_doc_type, unreadable, missing_value), each driven by its own detection signal — for example, a document's own header line naming it as something other than an SI or BL."),

        h1("Challenges Faced"),
        boldLabel("Same data, different labels: ", "solved with a normalized label→field dictionary instead of hardcoded field positions."),
        boldLabel("Distinguishing a real request from a reliability test: ", "e.g. “please send the draft BL” (normal, no attachment yet) vs. “please compare… attachments appear to have been dropped” (edge case, must escalate) — found and encoded from the actual inbox language, not guessed."),
        boldLabel("Corrupted PDF text layers: ", "some PDFs' text extraction interleaves an overlapping label and value into garbage. Built a leakage detector that recognizes corrupted output and escalates rather than reporting a scrambled name as fact."),
        boldLabel("Bilingual / glued labels: ", "CJK-annotated labels (e.g. “Gross Weight毛重(KGS)”) and font-kerning artifacts required fallback normalization passes."),

        h1("Future Roadmap"),
        bullet("OCR (Tesseract) for scanned/image-only PDFs — the architecture already supports it as a drop-in extractor."),
        bullet("Optional LLM fallback for messier real-world inboxes beyond this dataset's patterns."),
        bullet("Web UI for interactive review of escalated cases (human-in-the-loop workflow)."),
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  require("fs").writeFileSync("SDOC_Elevate_Submission.docx", buf);
  console.log("wrote SDOC_Elevate_Submission.docx");
});
