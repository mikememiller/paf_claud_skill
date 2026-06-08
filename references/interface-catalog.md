<!-- Syntax Corporation © 2026 — EBS PAF Agent skill -->
# EBS interface catalog — the 4 pillars

Starting points per domain. **Phase-1 live discovery confirms** exact tables,
columns, and the import program on the target instance — these are representative.

## Financials
| Agent | Target interface | Import program |
|-------|------------------|----------------|
| AP invoice (reference build) | AP_INVOICES_INTERFACE (+ AP_INVOICE_LINES_INTERFACE) | Payables Open Interface Import |
| AR invoice | RA_INTERFACE_LINES_ALL | AutoInvoice |
| GL journals / close | GL_INTERFACE | Journal Import |
| Cash mgmt / bank recon | CE_STATEMENT_HEADERS_INT / CE_STATEMENT_LINES_INTERFACE | Bank Statement Import |
| Fixed assets | FA_MASS_ADDITIONS | Post Mass Additions |
| iExpenses | AP_EXPENSE_REPORT_HEADERS/LINES (interface) | Expense Report Import |

## HR / Payroll
| Agent | Target / mechanism | Loader |
|-------|--------------------|--------|
| Worker / org data | **HCM Data Loader (HDL)** or HR APIs (not classic interface tables) | HDL / batch |
| Payroll element entries | PAY_BATCH_HEADERS / PAY_BATCH_LINES (**BEE**) | Batch Element Entry |
| Time & labor | HXC / OTL interfaces | Time Import |

> HR/Payroll favors **APIs / HDL / BEE** over interface tables. The
> repository/writer abstraction supports "call an EBS API" as well as "insert
> into an interface table" — the pattern still holds; pick the mechanism in
> Phase 1.

## Manufacturing
| Agent | Target interface | Import program |
|-------|------------------|----------------|
| WIP jobs | WIP_JOB_SCHEDULE_INTERFACE | WIP Mass Load |
| BOMs | BOM_BILL_OF_MTLS_INTERFACE / BOM_INVENTORY_COMPS_INTERFACE | Bill/Routing Import |
| Quality results | QA_RESULTS_INTERFACE | Quality Import |

## Supply Chain / Distribution
| Agent | Target interface | Import program |
|-------|------------------|----------------|
| Order intake | OE_HEADERS_IFACE_ALL (+ OE_LINES_IFACE_ALL) | Order Import |
| Item master | MTL_SYSTEM_ITEMS_INTERFACE | Item Import |
| Inventory txns | MTL_TRANSACTIONS_INTERFACE | Transaction Manager |
| Procurement / requisitions | PO_REQUISITIONS_INTERFACE_ALL | Requisition Import |
| BPA price catalog (the Oracle blog's case) | PO price catalog / PDOI | Import Price Catalog (PDOI) |

## Per-domain notes
- Each domain needs its own **extraction schema**, **policy rules** (3-way match
  for AP; pricing/credit holds for Order; renewal-template for BPA; close
  checklist for GL/CE; element validation for Payroll), and **balancing rule**.
- Always read-only by default; load via the standard import program.
