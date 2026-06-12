"""
================================================================================
 Syntax Corporation © 2026 — EBS PAF Agent skill
 scripts/lint_paf.py — deterministic linter for PAF build artifacts.
 Version : 2.0.0   Build : 2026.06.11   Date : 2026-06-11
--------------------------------------------------------------------------------
 Catches the bugs that historically reached Phase 6 — at write time instead.
 Checks are locked to the REAL 26.4 schema (core/paf-import.md, verified from a
 decrypted live export), not to guesses.

 Targets (auto-detected):
   *.flowgraph.json / any {nodes,edges} JSON  → structural flowGraph lint
   *.paf                                      → decrypt (default password) +
                                                envelope-shape + flowGraph lint
   spec.yaml / spec.yml                       → required top-level keys present
   *.py under src|scripts|qa_checks           → Syntax banner present
   Agent Spec flow JSON (tool-free string)    → pyagentspec round-trip when the
                                                SDK is installed (else a note)

 Findings are BLOCKING (exit 2). Notes are informational (exit stays 0).

   python lint_paf.py PATH [PATH ...] [--target-version 26.4] [--json]

 Version axis (memorize this — it is the one everyone confuses):
   SDK spec version, PAF instance version, and .paf artifact format are
   INDEPENDENT. File import is the supported path on 26.4; on 25.3 file import
   is rejected ("Tools are missing to be declared") — canvas + manual MCP
   attach is the only 25.3 path. --target-version < 26.4 therefore FAILS any
   file-import artifact. Resource bindings (MCP server, LLM) NEVER travel in
   any artifact; their absence is by design, never a finding.
================================================================================
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

BANNER_RE = re.compile(r"Syntax Corporation .* 2026")
PLACEHOLDER_RE = re.compile(r"TODO|\{\{|<replace|FIXME|lorem ipsum", re.IGNORECASE)
KNOWN_KINDS = {"agentStep", "chatInputComponent", "mcpServer", "chatOutputComponent"}
MIN_FILE_IMPORT_VERSION = (26, 4)
REQUIRED_SPEC_KEYS = {
    # derived from spec.example.yaml (keep in sync); dynamic union below if the
    # example file is reachable.
    "meta", "problem", "solution", "architecture", "controls", "proof",
    "why_us", "next_steps", "pricing", "bom", "estimator", "tech_design",
    "install", "sow", "flow_diagram", "governance", "timeline", "org_id",
    "source", "target_interface", "policy", "golden_record", "paf",
}


def _tmpl_value(field: object) -> object:
    """PAF template fields are component dicts; the content lives in 'value'."""
    if isinstance(field, dict) and "value" in field:
        return field["value"]
    return field


def _parse_version(text: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:4]) or (0,)


# --------------------------------------------------------------------- checks
def lint_flowgraph(fg: dict, label: str) -> tuple[list[str], list[str]]:
    """Structural lint of a tool-bound {nodes, edges} flowGraph."""
    findings: list[str] = []
    notes: list[str] = []
    nodes = fg.get("nodes")
    edges = fg.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return [f"{label}: not a flowGraph — needs 'nodes' and 'edges' arrays"], notes

    ids: list[str] = []
    kinds: dict[str, int] = {}
    mcp_ids: set[str] = set()
    agent_steps: list[dict] = []

    for i, n in enumerate(nodes):
        nid = n.get("id")
        if not nid:
            findings.append(f"{label}: node[{i}] has no id")
            continue
        ids.append(nid)
        if n.get("type") != "flowGenericNode":
            findings.append(
                f"{label}: node {nid[:18]} top-level type={n.get('type')!r} — "
                "must be 'flowGenericNode' (the kind lives in data.type)"
            )
        kind = n.get("data", {}).get("type")
        kinds[kind] = kinds.get(kind, 0) + 1
        if kind not in KNOWN_KINDS:
            findings.append(f"{label}: node {nid[:18]} unknown data.type={kind!r}")
        if kind == "mcpServer":
            mcp_ids.add(nid)
        if kind == "agentStep":
            agent_steps.append(n)

    dupes = {x for x in ids if ids.count(x) > 1}
    if dupes:
        findings.append(f"{label}: duplicate node ids {sorted(dupes)}")
    id_set = set(ids)

    if kinds.get("chatInputComponent", 0) != 1:
        findings.append(f"{label}: need exactly 1 chatInputComponent, "
                        f"found {kinds.get('chatInputComponent', 0)}")
    if kinds.get("chatOutputComponent", 0) != 1:
        findings.append(f"{label}: need exactly 1 chatOutputComponent, "
                        f"found {kinds.get('chatOutputComponent', 0)}")
    if kinds.get("agentStep", 0) < 1:
        findings.append(f"{label}: no agentStep node")

    referenced_mcp: set[str] = set()
    for n in agent_steps:
        nid = n["id"][:18]
        tmpl = n.get("data", {}).get("template", {})
        for fld in ("custom_instruction", "agent_description"):
            val = _tmpl_value(tmpl.get(fld))
            if not isinstance(val, str) or not val.strip():
                findings.append(f"{label}: agentStep {nid} has empty {fld}")
            elif PLACEHOLDER_RE.search(val):
                findings.append(
                    f"{label}: agentStep {nid} {fld} contains placeholder text "
                    f"({PLACEHOLDER_RE.search(val).group(0)!r}) — no placeholders ship"
                )
        tool_refs = _tmpl_value(tmpl.get("tools")) or []
        if not isinstance(tool_refs, list):
            findings.append(f"{label}: agentStep {nid} tools.value is not a list")
            tool_refs = []
        for ref in tool_refs:
            referenced_mcp.add(ref)
            if ref not in mcp_ids:
                findings.append(
                    f"{label}: agentStep {nid} tools.value references {str(ref)[:18]} "
                    "— no mcpServer node with that id (broken clone/remap?)"
                )
    for orphan in mcp_ids - referenced_mcp:
        findings.append(
            f"{label}: mcpServer {orphan[:18]} is not referenced by any "
            "agentStep tools.value — orphan tool server"
        )

    for j, e in enumerate(edges):
        eid, src, tgt = e.get("id", ""), e.get("source"), e.get("target")
        sh, th = e.get("sourceHandle", ""), e.get("targetHandle", "")
        where = f"{label}: edge[{j}]"
        if src not in id_set:
            findings.append(f"{where} source {str(src)[:18]} is not a node id")
        if tgt not in id_set:
            findings.append(f"{where} target {str(tgt)[:18]} is not a node id")
        if src and src not in eid:
            findings.append(f"{where} id does not embed source node id "
                            "(clone must remap ids EVERYWHERE — incl. edge ids)")
        if tgt and tgt not in eid:
            findings.append(f"{where} id does not embed target node id "
                            "(clone must remap ids EVERYWHERE — incl. edge ids)")
        if src and not sh.endswith(src):
            findings.append(f"{where} sourceHandle does not end with source node id")
        if tgt and not th.endswith(tgt):
            findings.append(f"{where} targetHandle does not end with target node id")

    return findings, notes


def lint_agentspec_string(data: str, label: str) -> tuple[list[str], list[str]]:
    """Tool-free Agent Spec flow (envelope data as JSON string)."""
    findings: list[str] = []
    notes: list[str] = []
    try:
        json.loads(data)
    except json.JSONDecodeError as ex:
        return [f"{label}: Agent Spec payload is not valid JSON ({ex})"], notes
    try:
        from pyagentspec.serialization import AgentSpecDeserializer
        try:
            AgentSpecDeserializer().from_json(data)
            notes.append(f"{label}: pyagentspec round-trip OK")
        except Exception as ex:  # SDK raises its own hierarchy; report, don't crash
            findings.append(f"{label}: pyagentspec rejected the flow — "
                            f"{type(ex).__name__}: {str(ex)[:200]}")
    except ImportError:
        notes.append(f"{label}: pyagentspec not installed — deep validation "
                     "skipped (structural JSON check only)")
    return findings, notes


def _load_packager():
    """Locate core/scripts/paf_packager.py: same dir, skill layout, or env."""
    here = Path(__file__).resolve().parent
    candidates = [
        here / "paf_packager.py",
        here.parent / "core" / "scripts" / "paf_packager.py",
        here.parent.parent / "core" / "scripts" / "paf_packager.py",
    ]
    env_home = os.environ.get("PAF_SKILL_HOME")
    if env_home:
        candidates.append(Path(env_home) / "core" / "scripts" / "paf_packager.py")
    for cand in candidates:
        if cand.is_file():
            import importlib.util
            spec = importlib.util.spec_from_file_location("paf_packager", cand)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


def lint_paf_bundle(path: Path, target: tuple[int, ...]) -> tuple[list[str], list[str]]:
    findings: list[str] = []
    notes: list[str] = []
    label = path.name
    pk = _load_packager()
    if pk is None:
        notes.append(f"{label}: paf_packager.py not found — .paf deep checks skipped "
                     "(set PAF_SKILL_HOME or co-locate the packager)")
        return findings, notes
    try:
        bundle = pk.unpack_paf(path.read_bytes())
    except Exception as ex:
        return [f"{label}: .paf failed to decrypt/unpack with the configured "
                f"password — {type(ex).__name__}: {str(ex)[:120]}"], notes
    if "metadata" not in bundle or not bundle.get("flows"):
        findings.append(f"{label}: bundle missing metadata.json or flows/*.json")
        return findings, notes
    app_ver = _parse_version(str(bundle["metadata"].get("applicationVersion", "")))
    if app_ver and app_ver < MIN_FILE_IMPORT_VERSION:
        findings.append(
            f"{label}: metadata applicationVersion "
            f"{bundle['metadata'].get('applicationVersion')} predates 26.4 — "
            "mint with the 26.4 packager"
        )
    for fname, envelope in bundle["flows"].items():
        data = envelope.get("data")
        is_fg = bool(envelope.get("flowGraph"))
        if is_fg and isinstance(data, dict):
            f2, n2 = lint_flowgraph(data, f"{label}:{fname}")
        elif not is_fg and isinstance(data, str):
            f2, n2 = lint_agentspec_string(data, f"{label}:{fname}")
        else:
            f2, n2 = [
                f"{label}:{fname}: envelope flowGraph={is_fg} but data is "
                f"{type(data).__name__} — flowGraph:true needs an object, "
                "flowGraph:false needs a JSON string"
            ], []
        findings += f2
        notes += n2
    notes.append(f"{label}: bindings (MCP server, LLM) are absent BY DESIGN — "
                 "rebind after import; never a finding")
    return findings, notes


def lint_spec_yaml(path: Path) -> tuple[list[str], list[str]]:
    findings: list[str] = []
    notes: list[str] = []
    try:
        import yaml
        spec = yaml.safe_load(path.read_text())
    except Exception as ex:
        return [f"{path.name}: unreadable YAML — {type(ex).__name__}: {str(ex)[:120]}"], notes
    if not isinstance(spec, dict):
        return [f"{path.name}: spec must be a mapping"], notes
    required = set(REQUIRED_SPEC_KEYS)
    example = Path(__file__).resolve().parent.parent / "spec.example.yaml"
    if example.is_file():
        try:
            import yaml
            required |= set(yaml.safe_load(example.read_text()).keys())
        except Exception:
            pass  # static list stands
    missing = sorted(required - set(spec.keys()))
    if missing:
        findings.append(f"{path.name}: missing required keys: {', '.join(missing)}")
    return findings, notes


def lint_banner(path: Path) -> tuple[list[str], list[str]]:
    try:
        text = path.read_text(errors="ignore")
    except OSError as ex:
        return [f"{path.name}: unreadable — {ex}"], []
    if BANNER_RE.search(text) is None:
        return [f"{path}: missing Syntax copyright/version/build/date banner"], []
    return [], []


# ------------------------------------------------------------------ dispatch
def lint_path(path: Path, target: tuple[int, ...]) -> tuple[list[str], list[str]]:
    if not path.exists():
        return [f"{path}: does not exist"], []
    if path.suffix == ".paf":
        if target < MIN_FILE_IMPORT_VERSION:
            return [
                f"{path.name}: target PAF {'.'.join(map(str, target))} — file "
                "import is unsupported below 26.4 (25.3 rejects with 'Tools are "
                "missing to be declared'); upgrade the instance or use canvas + "
                "manual MCP attach"
            ], []
        return lint_paf_bundle(path, target)
    if path.suffix == ".py":
        return lint_banner(path)
    if path.name in ("spec.yaml", "spec.yml"):
        return lint_spec_yaml(path)
    if path.suffix == ".json":
        try:
            obj = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as ex:
            return [f"{path.name}: invalid JSON — {ex}"], []
        if isinstance(obj, dict) and "nodes" in obj and "edges" in obj:
            if target < MIN_FILE_IMPORT_VERSION:
                return [
                    f"{path.name}: target PAF {'.'.join(map(str, target))} is "
                    "below 26.4 — this flowGraph cannot be file-imported there"
                ], []
            return lint_flowgraph(obj, path.name)
        return [], [f"{path.name}: JSON without nodes/edges — skipped"]
    return [], [f"{path.name}: no lint rules for this type — skipped"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--target-version",
                    default=os.environ.get("PAF_TARGET_VERSION", "26.4"))
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args(argv)

    target = _parse_version(args.target_version)
    all_findings: list[str] = []
    all_notes: list[str] = []
    for p in args.paths:
        f, n = lint_path(Path(p), target)
        all_findings += f
        all_notes += n

    if args.as_json:
        print(json.dumps({"findings": all_findings, "notes": all_notes,
                          "status": "FAIL" if all_findings else "PASS"}, indent=2))
    else:
        for n in all_notes:
            print(f"note: {n}")
        for f in all_findings:
            print(f"FINDING: {f}", file=sys.stderr)
        print(f"lint: {'FAIL' if all_findings else 'PASS'} "
              f"({len(all_findings)} finding(s), {len(all_notes)} note(s))")
    return 2 if all_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
