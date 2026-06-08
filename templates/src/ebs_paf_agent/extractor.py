"""
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
--------------------------------------------------------------------------------
 Project : EBS AP PAF — Accounts Payable Invoice Automation Agent
 Module  : extractor.py — invoice field extraction
 Version : 1.0.0      Build : 2026.06.02      Date : 2026-06-02
--------------------------------------------------------------------------------
 Two extraction strategies behind one protocol:

   * DeterministicExtractor — pure-Python regex/Decimal parser for the
     structured supplier-invoice text format. NO external dependencies, so the
     whole pipeline runs end-to-end with ONLY EBSDB available.
   * LLMExtractor — optional Anthropic-backed extractor for messy/scanned
     invoices; used only when ANTHROPIC_API_KEY is set and selected.

 make_extractor() picks the right one based on settings.
================================================================================
"""

from __future__ import annotations

import json
import os
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol


class ExtractionError(ValueError):
    """Raised when an invoice cannot be parsed into the expected shape."""


class InvoiceExtractor(Protocol):
    def extract(self, invoice_text: str) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _money(text: str) -> Decimal:
    """Parse a money token like '6,250.00' or '$1,755.00' to Decimal."""
    cleaned = text.replace(",", "").replace("$", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ExtractionError(f"Not a number: {text!r}") from exc


# Jurisdiction inference from a free-text tax label, e.g. "MA Sales Tax".
_STATE_RE = re.compile(r"\b([A-Z]{2})\b")


def _infer_jurisdiction(tax_label: str | None, address_block: str) -> str:
    if tax_label:
        m = _STATE_RE.search(tax_label)
        if m:
            return f"US-{m.group(1)}"
    # fall back to the bill-to / remit state in the address block
    m = re.search(r",\s*([A-Z]{2})\s+\d{5}", address_block)
    if m:
        return f"US-{m.group(1)}"
    return "US-XX"


# ---------------------------------------------------------------------------
# Deterministic extractor
# ---------------------------------------------------------------------------

class DeterministicExtractor:
    """Parse the structured invoice text format used by this project.

    Expected (tolerant) layout:
        Invoice Number: <str>
        Invoice Date:   <YYYY-MM-DD>
        Customer PO #:  <str|optional>
        Currency:       <ISO|optional, default USD>
        Federal Tax ID: <str|optional>
        <line table>:  LINE  ITEM  DESCRIPTION  QTY  UNIT  AMOUNT
        Subtotal / <Tax label> / TOTAL
    """

    _FIELD_PATTERNS = {
        "invoice_number": r"Invoice\s*(?:Number|No\.?|#)\s*:?\s*(\S+)",
        "invoice_date": r"Invoice\s*Date\s*:?\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        # Anchored to a labelled line and requires a ':' delimiter, so it
        # does NOT match a stray "PO" inside another value (e.g. an invoice
        # number like AND-NONPO-1) or a "PO BOX" remit address.
        "po_number": r"^[ \t]*(?:customer\s+)?p\.?o\.?\b\s*(?:#|no\.?|number)?\s*:\s*(\S+)",
        "currency": r"Currency\s*:?\s*([A-Z]{3})",
        "vendor_tax_id": r"(?:Federal\s*)?Tax\s*ID\s*:?\s*([0-9\-]+)",
    }

    # A line-item row: <n> <item> <desc...> <qty> <unit> <amount>
    _LINE_RE = re.compile(
        r"^\s*(\d+)\s+(\S+)\s+(.+?)\s+([\d,]+(?:\.\d+)?)\s+"
        r"([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
    )
    _SUBTOTAL_RE = re.compile(r"Subtotal\s*:?\s*\$?([\d,]+\.\d{2})", re.I)
    _TOTAL_RE = re.compile(r"TOTAL\s*(?:DUE)?\s*:?\s*\$?([\d,]+\.\d{2})", re.I)
    _TAX_RE = re.compile(
        r"([A-Za-z][\w ]*?Tax)[^\d]*?\(?([\d.]+)%\)?\s*:?\s*\$?([\d,]+\.\d{2})",
        re.I,
    )

    def extract(self, invoice_text: str) -> dict[str, Any]:
        text = invoice_text
        result: dict[str, Any] = {}

        for key, pat in self._FIELD_PATTERNS.items():
            m = re.search(pat, text, re.I | re.M)
            result[key] = m.group(1) if m else None

        if not result.get("invoice_number"):
            raise ExtractionError("Could not find an invoice number.")
        if not result.get("invoice_date"):
            raise ExtractionError("Could not find an invoice date (YYYY-MM-DD).")

        result["currency"] = result.get("currency") or "USD"
        result["vendor_name"] = self._vendor_name(text)

        # tax + jurisdiction
        tax_total = Decimal("0")
        tax_rate_pct: float | None = None
        tax_label = None
        if (m := self._TAX_RE.search(text)):
            tax_label = m.group(1)
            tax_rate_pct = float(m.group(2))
            tax_total = _money(m.group(3))
        result["jurisdiction"] = _infer_jurisdiction(tax_label, text)
        result["tax_total"] = float(tax_total)

        # line items
        lines: list[dict[str, Any]] = []
        for raw in text.splitlines():
            lm = self._LINE_RE.match(raw)
            if not lm:
                continue
            line_no = int(lm.group(1))
            item = lm.group(2)
            desc = lm.group(3).strip()
            qty = _money(lm.group(4))
            unit = _money(lm.group(5))
            amount = _money(lm.group(6))
            lines.append({
                "line_number": line_no,
                "description": desc,
                "item_number": item,
                "po_line_num": line_no,  # convention: invoice line N ↔ PO line N
                "quantity": float(qty),
                "unit_price": float(unit),
                "uom": "EA",
                "amount": float(amount),
                "tax_rate_pct": tax_rate_pct,
            })
        if not lines:
            raise ExtractionError("No invoice line items could be parsed.")
        result["lines"] = lines

        subtotal = (_money(m.group(1))
                    if (m := self._SUBTOTAL_RE.search(text)) else
                    sum((Decimal(str(l["amount"])) for l in lines), Decimal("0")))
        total = (_money(m.group(1))
                 if (m := self._TOTAL_RE.search(text)) else subtotal + tax_total)
        result["subtotal"] = float(subtotal)
        result["total"] = float(total)
        return result

    @staticmethod
    def _vendor_name(text: str) -> str:
        """The supplier name is the first substantive line of the document."""
        for raw in text.splitlines():
            s = raw.strip(" =\t")
            if not s:
                continue
            if re.fullmatch(r"[=\-_]+", s):
                continue
            return s
        raise ExtractionError("Could not determine vendor name.")


# ---------------------------------------------------------------------------
# Optional LLM extractor (Anthropic)
# ---------------------------------------------------------------------------

_EXTRACTION_PROMPT = """You are an AP invoice extractor. Read the supplier
invoice text below and return ONLY a JSON object with this shape:
{"vendor_name": str, "vendor_tax_id": str|null, "invoice_number": str,
 "invoice_date": "YYYY-MM-DD", "po_number": str|null, "currency": str,
 "jurisdiction": str, "lines": [{"line_number": int, "description": str,
 "item_number": str|null, "po_line_num": int|null, "quantity": number,
 "unit_price": number, "uom": str, "amount": number, "tax_rate_pct": number|null}],
 "subtotal": number, "tax_total": number, "total": number}
No preamble, no markdown fences. Use null for genuinely absent fields; never invent values.

INVOICE TEXT:
---
"""


class LLMExtractor:
    """Anthropic-backed extractor (optional). Requires the `anthropic` package
    and ANTHROPIC_API_KEY."""

    def __init__(self, model: str = "claude-opus-4-8"):
        try:
            from anthropic import Anthropic
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ExtractionError(
                "LLMExtractor requires the 'anthropic' package."
            ) from exc
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ExtractionError("ANTHROPIC_API_KEY is not set.")
        self._client = Anthropic()
        self.model = model

    def extract(self, invoice_text: str) -> dict[str, Any]:  # pragma: no cover
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user",
                       "content": _EXTRACTION_PROMPT + invoice_text}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:]
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"LLM did not return valid JSON: {exc}") from exc


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_extractor(strategy: str = "deterministic",
                   llm_model: str = "claude-opus-4-8") -> InvoiceExtractor:
    """Build an extractor.

    strategy:
      'deterministic' -> always the regex parser (default; zero deps)
      'llm'           -> Anthropic (raises if unavailable)
      'auto'          -> LLM when ANTHROPIC_API_KEY is set, else deterministic
    """
    if strategy == "deterministic":
        return DeterministicExtractor()
    if strategy == "llm":
        return LLMExtractor(model=llm_model)
    if strategy == "auto":
        if os.environ.get("ANTHROPIC_API_KEY"):
            try:
                return LLMExtractor(model=llm_model)
            except ExtractionError:
                return DeterministicExtractor()
        return DeterministicExtractor()
    raise ValueError(f"Unknown extractor strategy: {strategy!r}")
