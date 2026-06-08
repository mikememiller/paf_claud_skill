<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# Oracle / EBS gotchas (check every build)

Each of these caused a real bug in the reference AP build. Treat as a checklist.

1. **`ROWNUM` + `ORDER BY` returns an arbitrary row.** ROWNUM is applied before
   the sort. Always wrap: `SELECT * FROM (SELECT ... ORDER BY ...) WHERE ROWNUM=1`.
2. **Binding date *strings* to `DATE` columns → ORA-01861** (session
   `NLS_DATE_FORMAT` is `DD-MON-RR`). Bind `datetime.date` objects, or
   `TO_DATE(:x,'YYYY-MM-DD')`. (See `interface_loader.py` `DATE_COLS`.)
3. **Stale optimizer `num_rows`.** `all_tables.num_rows` lies (the AP interface
   tables read 4015/28730 but were empty). Confirm data with `COUNT(*)`.
4. **Loose regex over-matching** (extractor): "PO" matched inside an invoice
   number `AND-NONPO-1` → captured "-1". Anchor to a labelled line + delimiter.
5. **Fuzzy name match hits the wrong record.** Resolution order: tax_id / id →
   number → exact name → fuzzy (`LIKE %…%`) last.
6. **Output must balance.** header `INVOICE_AMOUNT` = Σ line AMOUNTs **incl. a
   TAX line**; dropping tax → import rejects.
7. **Dual tolerance, not two hurdles.** Hold a price/qty variance only when it
   breaches **both** the percentage **and** a material dollar floor — else
   within-tolerance variances on large lines false-flag.
8. **Foreign currency:** set `EXCHANGE_RATE_TYPE` (e.g. 'Corporate'); leave rate
   blank for derived types; only 'User' needs an explicit rate.
9. **NNE / thick mode:** EBS enforces Native Network Encryption; python-oracledb
   **thin** fails `DPY-3001`. Dev/test uses thick + Instant Client; production
   uses the managed MCP / Database Tools Connection (handles connectivity).
10. **Org scoping + injection:** every query is `org_id`-scoped and uses **bind
    variables only** (never string interpolation). Document
    `FND_GLOBAL.APPS_INITIALIZE` for multi-org context.
11. **`apps.` synonyms.** Use the APPS public synonyms (e.g. `apps.ap_suppliers`,
    `apps.gl_code_combinations_kfv`); base-schema objects may not be visible.
12. **Duplicate / idempotency:** real duplicate check against base tables
    (`ap_invoices_all`), not a stub returning False.
