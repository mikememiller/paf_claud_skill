"""
================================================================================
 Syntax Corporation © 2026 — All Rights Reserved
 Project : EBS AP PAF — paf/paf_packager.py
 Version : 1.2.0   Build : 2026.06.08   Date : 2026-06-08
--------------------------------------------------------------------------------
 PAF .paf packager — mints a directly-importable Private Agent Factory bundle
 from an Agent Spec flow (or a UI flowGraph). This is the REAL import path on
 **PAF 26.4** (file → My Custom Flows → Import). Reverse-engineered from a
 genuine 26.4 export and verified by round-trip.

 .paf format:
   base64( [16B salt][12B nonce][AES-256-GCM ciphertext+tag] )
   key       = PBKDF2-HMAC-SHA256(password, salt, 100_000 iters, 32B)
   plaintext = ZIP{ metadata.json, flows/<FLOWID>_<name>.json }
   flow file = PAF envelope; envelope["data"] is EITHER
                 * an Agent Spec JSON **string**  (flowGraph=False) — cognitive map
                 * a {nodes, edges} **object**    (flowGraph=True)  — tool-bound

 DEFAULT PASSWORD = "simple4u" (override with $PAF_PASSWORD or password=...).
 The .paf carries NO secrets by design (Instance Principal + rebind MCP/LLM in
 the PAF Agent Builder after import), so a shared, well-known import password is
 a convenience — NOT a secret boundary. Use a real per-tenant password only if a
 bundle ever has to carry a secret (it shouldn't).

 CLI:
   python paf/paf_packager.py pack   --in flow.json --out agent.paf --name "My Agent"
   python paf/paf_packager.py pack   --in flowgraph.json --flowgraph --name "My Agent"
   python paf/paf_packager.py unpack --in agent.paf            # decrypt + inspect
================================================================================
"""
import base64, io, json, os, re, uuid, zipfile, datetime
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ITERS, KEYLEN, SALTLEN, NONCELEN = 100_000, 32, 16, 12
APP_VERSION = "26.4.0.0.0"
# Baked, overridable default. $PAF_PASSWORD wins; pass password=... to override.
DEFAULT_PASSWORD = os.environ.get("PAF_PASSWORD", "simple4u")


def _key(pw: bytes, salt: bytes) -> bytes:
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=KEYLEN, salt=salt, iterations=ITERS).derive(pw)


def _metadata() -> dict:
    return {"applicationVersion": APP_VERSION,
            "exportedAt": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            "encrypted": True,
            "contains": {"customFlows": True, "modelDetails": False, "dbDataSources": False,
                         "selectAiDetails": False, "mcpServers": False, "restApiTools": False},
            "count": 1, "flowScope": "selected"}


def _seal(metadata: dict, flow_filename: str, envelope: dict, password: str) -> bytes:
    """ZIP{metadata.json, flow} -> AES-256-GCM -> base64 (single line, no terminator)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("metadata.json", json.dumps(metadata, indent=2))
        z.writestr(flow_filename, json.dumps(envelope, indent=2))
    plaintext = buf.getvalue()
    salt, nonce = os.urandom(SALTLEN), os.urandom(NONCELEN)
    ct = AESGCM(_key(password.encode(), salt)).encrypt(nonce, plaintext, None)
    return base64.b64encode(salt + nonce + ct)


def pack_paf(agentspec_flow: dict, *, name: str, description: str = "",
             password: str = DEFAULT_PASSWORD, category: int = 1, icon: str = "workflow") -> bytes:
    """Build a .paf (bytes) from an Agent Spec flow dict (data = JSON string, flowGraph=False)."""
    flow_id = uuid.uuid4().hex.upper()                      # 32-hex-upper, matches observed convention
    data_str = json.dumps(agentspec_flow, indent=2).replace("\n", "\r\n")
    envelope = {
        "name": name, "description": description, "category": category, "icon": icon,
        "published": False, "flowGraph": False,
        "data": data_str, "toolsPythonScript": None, "importFileType": None,
    }
    fname = f"flows/{flow_id}_{name.replace(' ', '_')}.json"
    return _seal(_metadata(), fname, envelope, password)


def pack_flowgraph(flowgraph_data: dict, *, name: str, description: str = "",
                   password: str = DEFAULT_PASSWORD, published: bool = False,
                   category: int = 1, icon: str = "workflow") -> bytes:
    """Mint a .paf carrying a tool-bound flowGraph agent (data is an OBJECT, flowGraph=True)."""
    envelope = {"name": name, "description": description, "category": category, "icon": icon,
                "published": published, "flowGraph": True,
                "data": flowgraph_data, "toolsPythonScript": None, "importFileType": None}
    fname = f"flows/{uuid.uuid4().hex.upper()}_{name.replace(' ', '_')}.json"
    return _seal(_metadata(), fname, envelope, password)


def unpack_paf(paf_bytes: bytes, password: str = DEFAULT_PASSWORD) -> dict:
    """Reverse a .paf -> {metadata, flows:{name:envelope}}; raises (InvalidTag) if password wrong."""
    raw = base64.b64decode(paf_bytes)
    salt, nonce, ct = raw[:SALTLEN], raw[SALTLEN:SALTLEN+NONCELEN], raw[SALTLEN+NONCELEN:]
    plaintext = AESGCM(_key(password.encode(), salt)).decrypt(nonce, ct, None)   # GCM tag verifies here
    z = zipfile.ZipFile(io.BytesIO(plaintext))
    out = {"metadata": json.loads(z.read("metadata.json")), "flows": {}}
    for n in z.namelist():
        if n.startswith("flows/"):
            out["flows"][n] = json.loads(z.read(n))
    return out


def remap_uuids(flow: dict, *, new_name: str, new_agent_name: str, new_prompt: str) -> dict:
    """Clone an Agent Spec flow with fresh UUIDs + distinct identifiers (a genuinely new flow)."""
    s = json.dumps(flow)
    for old in set(re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", s)):
        s = s.replace(old, str(uuid.uuid4()))
    f = json.loads(s)
    f["name"] = new_name
    rc = f.get("$referenced_components", {})
    for c in rc.values():
        if c.get("component_type") == "AgentNode" and c.get("agent"):
            c["agent"]["name"] = new_agent_name
            c["agent"]["system_prompt"] = new_prompt
    return f


def clone_flowgraph(template_data: dict, *, new_instruction: str, new_agent_description: str) -> dict:
    """Clone a PAF flowGraph {nodes,edges}: fresh node IDs (consistent across edges/handles/tool refs),
    new agent instruction + description. Tool wiring (MCP-server node + edges) is preserved."""
    import copy
    data = copy.deepcopy(template_data)
    old_ids = [n["id"] for n in data["nodes"]]            # ids are embedded in edges + agent tools.value
    s = json.dumps(data)
    for oid in old_ids:
        nid = f"node-{uuid.uuid4().hex[:13]}-{uuid.uuid4()}"
        s = s.replace(oid, nid)
    data = json.loads(s)
    for n in data["nodes"]:                               # set the agent node's instruction + description
        tmpl = n.get("data", {}).get("template", {})
        if "custom_instruction" in tmpl:
            tmpl["custom_instruction"]["value"] = new_instruction
        if "agent_description" in tmpl:
            tmpl["agent_description"]["value"] = new_agent_description
    return data


# --- CLI ----------------------------------------------------------------------
def _main(argv=None) -> int:
    import argparse, sys
    ap = argparse.ArgumentParser(description="PAF 26.4 .paf packager (pack/unpack).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pack", help="wrap an Agent Spec flow (or flowGraph) into an importable .paf")
    p.add_argument("--in", dest="inp", required=True, help="input JSON (Agent Spec flow, or flowGraph)")
    p.add_argument("--out", dest="out", help="output .paf (default: <in>.paf)")
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--password", default=DEFAULT_PASSWORD)
    p.add_argument("--flowgraph", action="store_true", help="input is a {nodes,edges} flowGraph (tool-bound)")

    u = sub.add_parser("unpack", help="decrypt a .paf and print its metadata + envelope summary")
    u.add_argument("--in", dest="inp", required=True)
    u.add_argument("--password", default=DEFAULT_PASSWORD)

    a = ap.parse_args(argv)
    if a.cmd == "pack":
        spec = json.loads(open(a.inp).read())
        out = a.out or (a.inp.rsplit(".", 1)[0] + ".paf")
        paf = (pack_flowgraph(spec, name=a.name, description=a.description, password=a.password)
               if a.flowgraph else
               pack_paf(spec, name=a.name, description=a.description, password=a.password))
        open(out, "wb").write(paf)
        print(f"Wrote {out}  ({len(paf)} bytes, flowGraph={a.flowgraph}, app {APP_VERSION}).")
        print("  Import in PAF -> My Custom Flows -> Import; enter the password "
              f"('{a.password}'); then rebind the MCP server + LLM in Agent Builder.")
        return 0
    if a.cmd == "unpack":
        try:
            bundle = unpack_paf(open(a.inp, "rb").read(), a.password)
        except Exception as e:
            sys.stderr.write(f"decrypt failed ({type(e).__name__}): wrong password? "
                             f"(tried {a.password!r}; set --password or $PAF_PASSWORD)\n")
            return 3
        print(json.dumps(bundle["metadata"], indent=2))
        for fn, env in bundle["flows"].items():
            kind = "flowGraph(object)" if env.get("flowGraph") else "flow(Agent Spec string)"
            print(f"  - {fn}: name={env.get('name')!r} {kind}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
