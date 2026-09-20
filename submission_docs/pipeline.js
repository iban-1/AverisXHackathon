// Live port of src/sdoc/{synonyms,classify,extract,compare,pipeline}.py.
// Runs the SAME classify -> extract -> compare -> escalate logic in the
// browser, on the real dataset's text, as the tested Python pipeline.
(function (global) {
  "use strict";

  // ---------------------------------------------------------------- synonyms
  const FIELDS = [
    "shipper", "consignee", "notify_party", "port_of_loading",
    "port_of_discharge", "container_count", "gross_weight_kg",
  ];

  const LABEL_TO_FIELD = {
    "shipper": "shipper", "shipper/exporter": "shipper",
    "shipper (principal or seller)": "shipper", "exporter": "shipper",
    "consignee": "consignee", "consignee (non-negotiable)": "consignee",
    "to the order of": "consignee",
    "notify": "notify_party", "notify party": "notify_party",
    "notify party/intermediate consignee": "notify_party",
    "port of loading": "port_of_loading", "port of loading (pol)": "port_of_loading",
    "load port": "port_of_loading", "pol": "port_of_loading",
    "discharge port": "port_of_discharge", "port of discharge": "port_of_discharge",
    "port of discharge (pod)": "port_of_discharge", "pod": "port_of_discharge",
    "no. of containers": "container_count", "no. of containers or packages": "container_count",
    "total containers": "container_count", "container count": "container_count",
    "gross wt (kgs)": "gross_weight_kg", "gross wt": "gross_weight_kg",
    "gross weight": "gross_weight_kg", "gross weight (kg)": "gross_weight_kg",
    "gross weight (kgs)": "gross_weight_kg",
    "total gross wt (kgs)": "gross_weight_kg", "total gross weight (kg)": "gross_weight_kg",
    "total gross weight": "gross_weight_kg",
  };

  const OTHER_DOC_TYPE_LABELS = new Set([
    "invoice no.", "invoice date", "seller", "buyer", "total amount",
    "certificate no.", "issuing authority", "country of origin",
  ]);

  function normalizeLabel(raw) {
    const ascii = raw.replace(/[^\x00-\x7F]+/g, " ");
    const spaced = ascii.replace(/(?<=[A-Za-z])\(/g, " (");
    return spaced.trim().toLowerCase().split(/\s+/).join(" ");
  }

  function normalizeLabelParensStripped(raw) {
    const ascii = raw.replace(/[^\x00-\x7F]+/g, " ");
    const noParens = ascii.replace(/\([^)]*\)/g, " ");
    return noParens.trim().toLowerCase().split(/\s+/).filter(Boolean).join(" ");
  }

  function fieldForLabel(raw) {
    const f = LABEL_TO_FIELD[normalizeLabel(raw)];
    if (f) return f;
    return LABEL_TO_FIELD[normalizeLabelParensStripped(raw)] || null;
  }

  function isOtherDocTypeLabel(raw) {
    return OTHER_DOC_TYPE_LABELS.has(normalizeLabel(raw));
  }

  // ---------------------------------------------------------------- classify
  const SPAM_TEXT_PATTERNS = [
    /bitcoin/i, /crypto/i, /guaranteed.*returns/i, /investment opportunity/i,
    /update your account/i, /avoid suspension/i, /storage is full/i,
    /verify.*account/i, /exclusive offer/i, /\d+%\s*off/i, /weird trick/i,
    /undelivered messages/i, /\bwinner\b/i, /\bprize\b/i, /lottery/i,
    /claim your/i, /free gift/i, /gift card/i, /password expir/i,
    /account.*(lock|clos)/i, /click here/i,
  ];
  const SPAM_DOMAIN_PATTERNS = [
    /mailbox/i, /secure-/i, /prize/i, /crypto/i, /parcel-track/i,
    /logistics-deals/i, /webmail-verify/i, /-verify\./i, /\.info$/i, /\.biz$/i,
  ];
  const INVOICE_PATTERNS = [
    /billing.*missing gr\b/i, /missing gr\b/i, /cancel invoice/i,
    /local charges/i, /d\s*&\s*d\s*charges/i, /total freight/i,
  ];
  const BL_COMPARISON_PHRASES = [/to confirm docs/i, /request bl draft/i, /draft bl/i, /amend bl/i];
  const SI_REQUEST_PHRASES = [
    /^(?:re[_: ]+|fw[d]?[_: ]+)*si\s*-/i, /^(?:re[_: ]+|fw[d]?[_: ]+)*si_/i,
    /request si/i, /cust si/i, /si needed/i,
  ];
  const GENERAL_PHRASES = [
    /update summary/i, /berthing report/i, /_rpa_/i, /reminder/i,
    /\bholiday\b/i, /\bsla\b/i, /out of office/i, /\bmaintenance\b/i,
  ];
  const CODED_CARRIER_TOKEN = /\b[A-Z]{2,8}\([A-Z0-9]+\)/;

  function anyMatch(patterns, text) {
    return patterns.some((p) => p.test(text));
  }

  function stripReplyPrefix(subject) {
    let s = subject.trim();
    let prev;
    do {
      prev = s;
      s = s.replace(/^(?:re|fwd?)[_: ]+/i, "").trim();
    } while (s !== prev);
    return s;
  }

  function isBlComparisonCoded(subject) {
    const stripped = stripReplyPrefix(subject);
    if (/^si\b/i.test(stripped)) return false; // belongs to SI_REQUEST
    return /^[A-Z]{2,8}\s*-/.test(stripped) && CODED_CARRIER_TOKEN.test(stripped);
  }

  function isSpam(text, domain) {
    if (anyMatch(SPAM_TEXT_PATTERNS, text)) return true;
    return !!domain && anyMatch(SPAM_DOMAIN_PATTERNS, domain);
  }

  function classify(email) {
    const subject = email.subject || "";
    const body = email.body || "";
    const spamText = `${subject}\n${body}`;
    const from = email.from || "";
    const domain = from.includes("@") ? from.split("@").pop() : "";

    if (isSpam(spamText, domain)) return "SPAM";
    if (anyMatch(INVOICE_PATTERNS, subject)) return "INVOICE_QUERY";
    if (anyMatch(SI_REQUEST_PHRASES, subject)) return "SI_REQUEST";
    if (anyMatch(BL_COMPARISON_PHRASES, subject) || isBlComparisonCoded(subject)) return "BL_COMPARISON";
    if (anyMatch(GENERAL_PHRASES, subject)) return "GENERAL";
    if (email.attachments && email.attachments.length) return "BL_COMPARISON";
    return "GENERAL";
  }

  // ------------------------------------------------------------------ extract
  const LABEL_LINE = /^([^:\n]{1,60}):\s*(.*)$/;
  const PLACEHOLDER_RE = /^(?:[_?]+\s*(?:MTS?|KGS?)?|N\/?A|TBA|NIL|PENDING)$/i;
  const GROSS_WEIGHT_FALLBACK_RE = /gross\s*w(?:eigh)?t.{0,20}?:\s*([\d,]+(?:\.\d+)?)\s*kgs?\b/i;
  const LABEL_LEAKAGE_RE = /\b(?:notify|consignee|shipper|intermediate)\b/i;
  const NAME_FIELDS = new Set(["shipper", "consignee", "notify_party"]);

  function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }
  const NO_COLON_LABEL_RE = new RegExp(
    "^(" +
      Object.keys(LABEL_TO_FIELD)
        .sort((a, b) => b.length - a.length)
        .map((l) => l.split(" ").map(escapeRe).join("\\s+"))
        .join("|") +
      ")\\s+(.+)$",
    "i"
  );

  function isUsableValue(v) {
    return !!v && !PLACEHOLDER_RE.test(v);
  }

  function extractFieldsTxt(text) {
    const fields = {};
    for (const rawLine of text.split("\n")) {
      const line = rawLine.trim();
      if (!line) continue;
      let label, value;
      const m = LABEL_LINE.exec(line);
      if (m) {
        label = m[1];
        value = m[2].trim();
      } else {
        const m2 = NO_COLON_LABEL_RE.exec(line);
        if (!m2) continue;
        label = m2[1];
        value = m2[2].trim();
      }
      const field = fieldForLabel(label);
      if (!field || fields[field] !== undefined) continue;
      if (!isUsableValue(value)) continue;
      if (NAME_FIELDS.has(field) && LABEL_LEAKAGE_RE.test(value)) continue;
      fields[field] = value;
    }
    if (fields["gross_weight_kg"] === undefined) {
      const m = GROSS_WEIGHT_FALLBACK_RE.exec(text);
      if (m) fields["gross_weight_kg"] = `${m[1]} KG`;
    }
    return fields;
  }

  const EXPECTED_HEADERS = ["SHIPPING INSTRUCTION", "BILL OF LADING"];
  function looksLikeOtherDocType(text) {
    const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length && !EXPECTED_HEADERS.some((h) => lines[0].toUpperCase().includes(h))) return true;
    for (const rawLine of text.split("\n")) {
      const m = LABEL_LINE.exec(rawLine);
      if (m && isOtherDocTypeLabel(m[1])) return true;
    }
    return false;
  }

  function normalizeTextValue(v) {
    return v.trim().split(/\s+/).join(" ").toUpperCase();
  }
  function parseContainerCount(v) {
    const m = /(\d+)/.exec(v);
    return m ? parseInt(m[1], 10) : null;
  }
  function parseGrossWeightKg(v) {
    const m = /([\d,]+(?:\.\d+)?)/.exec(v);
    return m ? parseFloat(m[1].replace(/,/g, "")) : null;
  }

  // ------------------------------------------------------------------ compare
  function normalizedValue(field, raw) {
    if (field === "container_count") return parseContainerCount(raw);
    if (field === "gross_weight_kg") return parseGrossWeightKg(raw);
    return normalizeTextValue(raw);
  }

  function compareFields(siFields, blFields) {
    const missing = FIELDS.filter((f) => siFields[f] === undefined || blFields[f] === undefined);
    if (missing.length) {
      return { status: "NEEDS_REVIEW", has_defect: false, defect_fields: [], review_reason: "missing_value" };
    }
    const defectFields = FIELDS.filter(
      (f) => normalizedValue(f, siFields[f]) !== normalizedValue(f, blFields[f])
    );
    if (defectFields.length) {
      return { status: "MISMATCH", has_defect: true, defect_fields: defectFields, review_reason: null };
    }
    return { status: "OK", has_defect: false, defect_fields: [], review_reason: null };
  }

  // ----------------------------------------------------------------- pipeline
  const ASKS_TO_COMPARE_RE = /\bcompare\b/i;
  const SUPPORTED_SUFFIXES = new Set([".txt", ".pdf", ".docx", ".xlsx"]);
  const SI_BL_ROLE_RE = /_(SI|BL)\.\w+$/i;

  function suffixOf(path) {
    const m = /\.[^.\/\\]+$/.exec(path);
    return m ? m[0].toLowerCase() : "";
  }

  function findComparablePair(attachments) {
    if (attachments.length !== 2) return null;
    let si = null, bl = null;
    for (const a of attachments) {
      if (!SUPPORTED_SUFFIXES.has(suffixOf(a))) return null;
      const m = SI_BL_ROLE_RE.exec(a);
      if (!m) return null;
      if (m[1].toUpperCase() === "SI") si = a; else bl = a;
    }
    return si && bl ? [si, bl] : null;
  }

  const DEFAULT_RESULT = () => ({
    category: "GENERAL", status: "OK", review_reason: null, has_defect: false, defect_fields: [],
  });

  // attachmentText: { [path]: { ok: bool, text: string|null } }
  function processEmail(email, attachmentText) {
    const category = classify(email);
    const result = Object.assign(DEFAULT_RESULT(), { category });
    if (category !== "BL_COMPARISON") return result;

    const attachments = email.attachments || [];
    if (attachments.length < 2) {
      if (ASKS_TO_COMPARE_RE.test(email.body || "")) {
        result.status = "NEEDS_REVIEW";
        result.review_reason = "missing_attachment";
      }
      return result;
    }

    const pair = findComparablePair(attachments);
    if (!pair) {
      result.status = "NEEDS_REVIEW";
      result.review_reason = "unreadable";
      return result;
    }

    const [siPath, blPath] = pair;
    const siEntry = attachmentText[siPath];
    const blEntry = attachmentText[blPath];

    if (!siEntry || !blEntry || !siEntry.ok || !blEntry.ok) {
      result.status = "NEEDS_REVIEW";
      result.review_reason = "unreadable";
      return result;
    }

    // The header/label check only applies to txt/PDF -- docx/xlsx have no
    // reliable "first line" header concept (matches pipeline.py's
    // _raw_text_for_doc_type_check, which returns None for those formats).
    const checkableSuffixes = new Set([".txt", ".pdf"]);
    for (const [path, entry] of [[siPath, siEntry], [blPath, blEntry]]) {
      if (checkableSuffixes.has(suffixOf(path)) && looksLikeOtherDocType(entry.text)) {
        result.status = "NEEDS_REVIEW";
        result.review_reason = "wrong_doc_type";
        return result;
      }
    }

    const siFields = extractFieldsTxt(siEntry.text);
    const blFields = extractFieldsTxt(blEntry.text);

    if (Object.keys(siFields).length === 0 || Object.keys(blFields).length === 0) {
      result.status = "NEEDS_REVIEW";
      result.review_reason = "unreadable";
      return result;
    }

    Object.assign(result, compareFields(siFields, blFields));
    return result;
  }

  global.SDOC = {
    FIELDS, classify, extractFieldsTxt, compareFields, processEmail,
    findComparablePair, looksLikeOtherDocType, fieldForLabel,
  };
})(typeof window !== "undefined" ? window : globalThis);
