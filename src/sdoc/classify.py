"""Stage 1: classify an inbox email into one of the 5 categories.

Pure rule-based (regex/keyword) classifier — no LLM. Patterns were derived
from data_v2/README.md's documented per-category signals plus a survey of
the actual subject lines and sender domains in the dataset (see the M1/M2
exploration notes in the project's plan/commit history).

Categories: BL_COMPARISON, SI_REQUEST, INVOICE_QUERY, GENERAL, SPAM.
"""
import re

CATEGORIES = ["BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"]

_SPAM_TEXT_PATTERNS = [
    r"bitcoin",
    r"crypto",
    r"guaranteed.*returns",
    r"investment opportunity",
    r"update your account",
    r"avoid suspension",
    r"storage is full",
    r"verify.*account",
    r"exclusive offer",
    r"\d+%\s*off",
    r"weird trick",
    r"undelivered messages",
    r"\bwinner\b",
    r"\bprize\b",
    r"lottery",
    r"claim your",
    r"free gift",
    r"gift card",
    r"password expir",
    r"account.*(lock|clos)",
    r"click here",
]
_SPAM_DOMAIN_PATTERNS = [
    r"mailbox",
    r"secure-",
    r"prize",
    r"crypto",
    r"parcel-track",
    r"logistics-deals",
    r"webmail-verify",
    r"-verify\.",
    r"\.info$",
    r"\.biz$",
]

_INVOICE_PATTERNS = [
    # "BILLING ... MISSING GR" together (bare "billing" alone also matches
    # GENERAL's "_RPA_ ... Billing Process Completed" bot notices).
    r"billing.*missing gr\b",
    r"missing gr\b",
    r"cancel invoice",
    r"local charges",
    r"d\s*&\s*d\s*charges",
    r"total freight",
]

_BL_COMPARISON_PHRASES = [
    r"to confirm docs",
    r"request bl draft",
    r"draft bl",
    r"amend bl",
]

_SI_REQUEST_PHRASES = [
    r"^(?:re[_: ]+|fw[d]?[_: ]+)*si\s*-",
    r"^(?:re[_: ]+|fw[d]?[_: ]+)*si_",
    r"request si",
    r"cust si",
    r"si needed",
]

_GENERAL_PHRASES = [
    r"update summary",
    r"berthing report",
    r"_rpa_",
    r"reminder",
    r"\bholiday\b",
    r"\bsla\b",
    r"out of office",
    r"\bmaintenance\b",
]

# A bare code word (not "SI") followed by " - " and, later in the subject, a
# "CARRIER(REF)" style token — the coded BL_COMPARISON subject pattern
# documented in data_v2/README.md (e.g. "AIE - POD - CARRIER(BL#) - ...").
_CODED_CARRIER_TOKEN = re.compile(r"\b[A-Z]{2,8}\([A-Z0-9]+\)")
# "re"/"fw"/"fwd" prefix is case-insensitive (subjects use "RE_"); the bare
# code itself must stay uppercase so we don't match arbitrary lowercase text.
_STARTS_WITH_BARE_CODE = re.compile(r"^(?:(?i:re|fwd?)[_: ]+)*[A-Z]{2,8}\s*-")


def _any_match(patterns, text):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _is_spam(text: str, domain: str) -> bool:
    if _any_match(_SPAM_TEXT_PATTERNS, text):
        return True
    return bool(domain) and _any_match(_SPAM_DOMAIN_PATTERNS, domain)


def _is_si_request(subject: str) -> bool:
    return _any_match(_SI_REQUEST_PHRASES, subject)


def _is_bl_comparison_coded(subject: str) -> bool:
    if re.match(r"^(?:re[_ ]+)?si\b", subject.strip(), re.IGNORECASE):
        return False  # "SI - ..." belongs to SI_REQUEST, not this pattern
    return bool(_STARTS_WITH_BARE_CODE.match(subject.strip())) and bool(
        _CODED_CARRIER_TOKEN.search(subject)
    )


def _is_bl_comparison(subject: str) -> bool:
    return _any_match(_BL_COMPARISON_PHRASES, subject) or _is_bl_comparison_coded(subject)


def _is_invoice_query(subject: str) -> bool:
    return _any_match(_INVOICE_PATTERNS, subject)


def _is_general(subject: str) -> bool:
    return _any_match(_GENERAL_PHRASES, subject)


def classify(email: dict) -> str:
    """Classify by subject line (deterministically coded in this dataset —
    see data_v2/README.md). Body text is used only for spam detection: the
    body of a legitimate request often lists unrelated words (e.g. "3
    Original invoice" as a required document) that would otherwise create
    false positives for other categories.
    """
    subject = email.get("subject", "") or ""
    body = email.get("body", "") or ""
    spam_text = f"{subject}\n{body}"
    frm = email.get("from", "") or ""
    domain = frm.split("@")[-1] if "@" in frm else ""

    if _is_spam(spam_text, domain):
        return "SPAM"
    if _is_invoice_query(subject):
        return "INVOICE_QUERY"
    if _is_si_request(subject):
        return "SI_REQUEST"
    if _is_bl_comparison(subject):
        return "BL_COMPARISON"
    if _is_general(subject):
        return "GENERAL"
    # Only BL_COMPARISON emails carry SI/BL attachments in this dataset — a
    # strong fallback signal when the subject wording didn't match.
    if email.get("attachments"):
        return "BL_COMPARISON"
    return "GENERAL"
