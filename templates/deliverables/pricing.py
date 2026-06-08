"""
================================================================================
 Syntax Corporation © 2026 — PAF Agent Factory — templates/deliverables/pricing.py
 Version : 2.0.0   Build : 2026.06.08
--------------------------------------------------------------------------------
 Single pricing model, SPEC-DRIVEN. Reads spec.yaml (PyYAML) and emits:
   <out>/spec.json     — the whole spec as JSON (so the Node + Python generators
                         can read it without a YAML dependency)
   <out>/pricing.json  — the computed pricing model (blended rate, implementation
                         fee, managed-services by tier/term, ROI)
 Every other deliverable generator reads these two files, so all figures match.

   python pricing.py --spec ../../spec.example.yaml --out build
================================================================================
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
_DEFAULT_SPEC = _HERE.parent.parent / "spec.example.yaml"   # skill-root spec


def blended_rate(p: dict) -> float:
    return round(sum(p["rate_card"][k] * p["delivery_mix"][k] for k in p["rate_card"]), 2)


def implementation_fee(p: dict) -> float:
    return round(blended_rate(p) * p["implementation_hours"], 2)


def managed_services(p: dict, tier: str) -> dict:
    base = (p["run_hours_per_month"] * blended_rate(p)
            + p["oci_run_monthly"][tier]
            + p["agent_license_per_year"] / 12)
    out = {}
    for term, disc in p["term_discount_pct"].items():
        monthly = round(base * (1 - disc / 100), 2)
        out[f"{term}_month"] = {"monthly": monthly,
                                "total_contract": round(monthly * int(term), 2),
                                "discount_pct": disc}
    return out


def roi(p: dict) -> dict:
    r = p["roi"]
    processing = round(r["txns_per_year"] * (r["manual_cost_per_txn"]
                                             - r["automated_cost_per_txn"]), 2)
    gross = processing + r["early_pay_capture"] + r["duplicate_prevention"] + r["audit_savings"]
    ms_year = managed_services(p, "medium")["12_month"]["monthly"] * 12
    net = round(gross - ms_year, 2)
    payback = round(ms_year / (gross / 12), 1) if gross else None
    return {"gross_annual_value": round(gross, 2), "processing_savings": processing,
            "managed_services_year": round(ms_year, 2), "net_annual_savings": net,
            "payback_months": payback, "three_year_net": round(net * 3, 2)}


def model(spec: dict) -> dict:
    p = spec["pricing"]
    return {"rate_card": p["rate_card"], "delivery_mix": p["delivery_mix"],
            "blended_rate": blended_rate(p), "implementation_fee": implementation_fee(p),
            "managed_services": {t: managed_services(p, t) for t in ("small", "medium", "large")},
            "roi": roi(p)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Spec-driven pricing model → spec.json + pricing.json")
    ap.add_argument("--spec", default=str(_DEFAULT_SPEC), help="spec.yaml input")
    ap.add_argument("--out", default="build", help="output dir for spec.json + pricing.json")
    a = ap.parse_args(argv)

    spec = yaml.safe_load(Path(a.spec).read_text())
    m = model(spec)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "spec.json").write_text(json.dumps(spec, indent=2))
    (out / "pricing.json").write_text(json.dumps(m, indent=2))

    print(f"blended rate   : ${m['blended_rate']}/hr")
    print(f"implementation : ${m['implementation_fee']:,.0f} (fixed, {spec['pricing']['implementation_hours']} hrs)")
    for term, d in m["managed_services"]["medium"].items():
        print(f"managed {term:9}: ${d['monthly']:,.0f}/mo  ({d['discount_pct']}% off)")
    print(f"ROI net/yr     : ${m['roi']['net_annual_savings']:,.0f}  payback {m['roi']['payback_months']} mo")
    print(f"-> {out/'spec.json'} · {out/'pricing.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
