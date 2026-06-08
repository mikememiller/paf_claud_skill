-- ============================================================================
--  Syntax Corporation (c) 2026 — EBS PAF Agent skill
--  discovery.sql — Phase-1 live schema discovery (run via the `oracle` MCP).
--  Replace :literals; verify every query returns rows BEFORE embedding it.
--  Rule: confirm data with COUNT(*), never trust ALL_TABLES.NUM_ROWS.
-- ============================================================================

-- 1) Do the target tables exist + actually hold data? (stale stats are common)
SELECT 'AP_INVOICES_INTERFACE' t, COUNT(*) n FROM apps.ap_invoices_interface
UNION ALL SELECT 'PO_HEADERS_ALL',     COUNT(*) FROM apps.po_headers_all
UNION ALL SELECT 'RCV_TRANSACTIONS',   COUNT(*) FROM apps.rcv_transactions;

-- 2) Exact columns of the target interface tables (drive the writer)
SELECT column_name, data_type, nullable
FROM all_tab_columns
WHERE owner='AP' AND table_name='AP_INVOICES_INTERFACE'
ORDER BY column_name;

-- 3) Find a clean GOLDEN RECORD (adapt per domain) — e.g. a fully-received PO
SELECT * FROM (
  SELECT ph.segment1 po_number, ph.po_header_id, ph.vendor_id, v.vendor_name,
         COUNT(DISTINCT pl.po_line_id) lines,
         COUNT(DISTINCT rt.transaction_id) rcv
  FROM apps.po_headers_all ph
  JOIN apps.ap_suppliers v ON v.vendor_id=ph.vendor_id
  JOIN apps.po_lines_all pl ON pl.po_header_id=ph.po_header_id
  JOIN apps.rcv_transactions rt ON rt.po_header_id=ph.po_header_id AND rt.transaction_type='RECEIVE'
  WHERE ph.type_lookup_code='STANDARD' AND ph.org_id=204
  GROUP BY ph.segment1, ph.po_header_id, ph.vendor_id, v.vendor_name
  HAVING COUNT(DISTINCT pl.po_line_id) BETWEEN 2 AND 5
  ORDER BY rcv DESC
) WHERE ROWNUM <= 5;

-- 4) ROWNUM + ORDER BY done correctly (inline view) — supplier resolution pattern
SELECT * FROM (
  SELECT s.vendor_id, s.segment1 vendor_num, s.vendor_name, ss.vendor_site_id
  FROM apps.ap_suppliers s
  JOIN apps.ap_supplier_sites_all ss ON ss.vendor_id=s.vendor_id AND ss.org_id=204
  WHERE UPPER(s.vendor_name) LIKE UPPER('%ACME%')
  ORDER BY ss.vendor_site_id
) WHERE ROWNUM = 1;

-- 5) GL code combination exists + enabled (referential QA)
SELECT code_combination_id, enabled_flag
FROM apps.gl_code_combinations_kfv
WHERE concatenated_segments = '01-520-7530-0000-000';
