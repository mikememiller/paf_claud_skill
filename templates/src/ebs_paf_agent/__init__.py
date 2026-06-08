"""
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
--------------------------------------------------------------------------------
 Project : EBS AP PAF — Accounts Payable Invoice Automation Agent
 Module  : ebs_ap_paf (package root)
 Version : 1.0.0      Build : 2026.06.02      Date : 2026-06-02
--------------------------------------------------------------------------------
 A Private-Agent-Factory-style agent for Oracle E-Business Suite that ingests
 supplier invoices, performs 3-way match + GL/tax coding against live EBS data,
 and emits AP Open Interface files (read-only by default).
================================================================================
"""

from __future__ import annotations

__all__ = ["__version__", "__build__", "BANNER"]

__version__ = "1.0.0"
__build__ = "2026.06.02"

BANNER = "Syntax Corporation © 2026 — EBS AP PAF v{} (build {})".format(
    __version__, __build__
)
