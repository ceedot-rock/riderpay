"""Integer-cents money math. No floats anywhere — ever.

Every amount in RiderPay is an int count of cents. Parsing converts text to
int cents without touching float; formatting converts int cents back to text.
"""

import re

_NON_USD = re.compile(r"[€£¥₹₩₽]")

_CENTS_RE = re.compile(r"(\d[\d,]*)\s*cents?\b", re.IGNORECASE)
_DOLLAR_RE = re.compile(
    r"""\$?\s*(?:(\d[\d,]*)(?:\.(\d{1,2}))?|\.(\d{1,2}))\s*(?:dollars?|usd|bucks?)?\b""",
    re.IGNORECASE | re.VERBOSE,
)

# full-string amount grammar: "2500 cents" | "$1,234.56" | "$.99" | "25 dollars"
_FULL_RE = re.compile(
    r"""\s*(?:(\d[\d,]*)\s*cents?|\$?\s*(?:(\d[\d,]*)(?:\.(\d{1,2}))?|\.(\d{1,2}))\s*(?:dollars?|usd|bucks?)?)\s*""",
    re.IGNORECASE | re.VERBOSE,
)


def _to_cents(dollar_digits: str, cent_digits: str | None) -> int:
    dollars = int(dollar_digits.replace(",", ""))
    cents = (cent_digits or "0")
    cents = (cents + "00")[:2]  # "5" -> "50", "" -> "00"
    result = dollars * 100 + int(cents)
    assert isinstance(result, int)
    return result


def parse_amount(text: str) -> int:
    """Parse a bare amount string to integer cents.

    Accepts: "$25", "25", "$25.50", "25 dollars", "$1,234.56", "2500 cents".
    Rejects: non-USD currency symbols, unparseable text. Never uses float.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty amount")
    if _NON_USD.search(text):
        raise ValueError("USD only — non-USD currency rejected")
    t = text.strip()

    m = _FULL_RE.fullmatch(t)
    if not m:
        raise ValueError(f"cannot parse amount: {text!r}")
    if m.group(1) is not None:  # "2500 cents" branch
        result = int(m.group(1).replace(",", ""))
        assert isinstance(result, int)
        return result
    dollars, cents, cents_only = m.group(2), m.group(3), m.group(4)
    if cents_only is not None:  # "$.99" branch
        return _to_cents("0", cents_only)
    return _to_cents(dollars, cents)


def extract_amount(text: str) -> int:
    """Find the first amount mentioned inside a longer instruction string."""
    if _NON_USD.search(text):
        raise ValueError("USD only — non-USD currency rejected")
    m = _CENTS_RE.search(text)
    if m:
        return parse_amount(m.group(0))
    m = _DOLLAR_RE.search(text)
    if m and ("$" in m.group(0) or re.search(r"dollars?|usd|bucks?", m.group(0), re.IGNORECASE)):
        return parse_amount(m.group(0))
    # bare number like "pay 25 to ..." — accept only if $-free digits found
    m = re.search(r"\b\d[\d,]*\.\d{1,2}\b", text)
    if m:
        return parse_amount(m.group(0))
    raise ValueError(f"no amount found in: {text!r}")


def fmt_cents(cents: int) -> str:
    """Format integer cents as "$d.cc"."""
    assert isinstance(cents, int), f"cents must be int, got {type(cents).__name__}"
    assert not isinstance(cents, bool)
    sign = "-" if cents < 0 else ""
    c = abs(cents)
    return f"{sign}${c // 100}.{c % 100:02d}"
