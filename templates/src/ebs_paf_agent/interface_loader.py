"""
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
--------------------------------------------------------------------------------
 Project : EBS AP PAF — Accounts Payable Invoice Automation Agent
 Module  : interface_loader.py — OPTIONAL direct INSERT into AP interface tables
 Version : 1.0.0      Build : 2026.06.02      Date : 2026-06-02
--------------------------------------------------------------------------------
 OFF BY DEFAULT. The faithful, audit-preserving path is to emit CSVs and let the
 standard Payables Open Interface Import concurrent program load them. This
 module is a convenience for environments that want the agent to stage rows
 directly into AP_INVOICES_INTERFACE / AP_INVOICE_LINES_INTERFACE.

 Guard rails:
   * never touches the base AP tables (AP_INVOICES_ALL etc.) — interface only;
   * refuses to load an invoice whose QAReport is not loadable;
   * single transaction, explicit commit, bind variables only;
   * empty strings are normalised to NULL so numeric columns bind cleanly.
================================================================================
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .db import EBSConnection
from .interface_writer import HEADER_COLS, LINE_COLS
from .qa_checks import QAReport

# Interface columns that are Oracle DATE types — bound as date objects, not
# strings, so binding does not depend on the session's NLS_DATE_FORMAT.
DATE_COLS = {"INVOICE_DATE", "GL_DATE", "EXCHANGE_DATE"}


class InterfaceLoadError(RuntimeError):
    pass


def _coerce_date(value: Any) -> Any:
    if isinstance(value, (date, datetime)) or value in (None, ""):
        return None if value == "" else value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _bindable(row: dict[str, Any], cols: list[str]) -> dict[str, Any]:
    """Build a bind dict: '' -> None (NULL), and DATE columns -> date objects."""
    out: dict[str, Any] = {}
    for c in cols:
        v = row.get(c, None)
        if c in DATE_COLS:
            out[c] = _coerce_date(v)
        else:
            out[c] = None if v == "" else v
    return out


def _insert_sql(table: str, cols: list[str]) -> str:
    collist = ", ".join(cols)
    binds = ", ".join(f":{c}" for c in cols)
    return f"INSERT INTO apps.{table} ({collist}) VALUES ({binds})"


def load_invoices(
    conn: EBSConnection,
    headers: list[dict[str, Any]],
    lines: list[dict[str, Any]],
    qa_reports: list[QAReport],
    *,
    confirm: bool = False,
) -> dict[str, int]:
    """Insert built interface rows into the AP interface tables.

    Requires `confirm=True` (the CLI maps this to --load-to-ebs --yes). Only
    invoices whose QAReport.loadable is True are written; their lines follow by
    INVOICE_ID. Returns counts.
    """
    if not confirm:
        raise InterfaceLoadError(
            "Refusing to write to EBS without explicit confirmation "
            "(pass confirm=True / --load-to-ebs --yes)."
        )

    loadable_ids = {
        h["INVOICE_ID"]
        for h, r in zip(headers, qa_reports)
        if r.loadable
    }
    if not loadable_ids:
        return {"headers": 0, "lines": 0, "skipped": len(headers)}

    hdr_sql = _insert_sql("ap_invoices_interface", HEADER_COLS)
    ln_sql = _insert_sql("ap_invoice_lines_interface", LINE_COLS)

    inserted_h = inserted_l = 0
    with conn._cursor() as cur:
        for h in headers:
            if h["INVOICE_ID"] in loadable_ids:
                cur.execute(hdr_sql, _bindable(h, HEADER_COLS))
                inserted_h += 1
        for ln in lines:
            if ln["INVOICE_ID"] in loadable_ids:
                cur.execute(ln_sql, _bindable(ln, LINE_COLS))
                inserted_l += 1
        conn.connection.commit()

    return {
        "headers": inserted_h,
        "lines": inserted_l,
        "skipped": len(headers) - len(loadable_ids),
    }
