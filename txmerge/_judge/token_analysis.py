"""Rebuild each arm's agent tree from subagent JSONLs and count real API spend.

usage: python3 -I token_analysis.py SUBAGENT_DIR OUT_JSON ARM_ID=name ...
"""
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

SUB = Path(sys.argv[1]); OUT = Path(sys.argv[2])
ROOTS = dict(a.split("=") for a in sys.argv[3:])
AID = re.compile(r"agentId: ([0-9a-f]{17})")

def text_len(c):
    if isinstance(c, str): return len(c)
    if isinstance(c, list): return sum(text_len(x.get("text", "")) if isinstance(x, dict) else len(str(x)) for x in c)
    return len(json.dumps(c))

agents = {}
for f in SUB.glob("agent-*.jsonl"):
    aid = f.stem[6:]
    calls = {}                    # message.id -> usage (dedupe streamed blocks)
    tools = Counter(); tool_chars = Counter(); children = []
    pending = {}                  # tool_use_id -> (name, input)
    first_prompt = None; ts = []; model = None
    for line in f.open():
        try: d = json.loads(line)
        except Exception: continue
        if d.get("timestamp"): ts.append(d["timestamp"])
        m = d.get("message")
        if not isinstance(m, dict): continue
        c = m.get("content")
        if m.get("role") == "user" and first_prompt is None:
            first_prompt = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c if isinstance(x, dict))
        if m.get("role") == "assistant":
            model = m.get("model", model)
            if m.get("usage") and m.get("id"): calls[m["id"]] = m["usage"]
            for b in c if isinstance(c, list) else []:
                if b.get("type") == "tool_use":
                    tools[b["name"]] += 1
                    pending[b["id"]] = (b["name"], b.get("input", {}))
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    name, inp = pending.get(b.get("tool_use_id"), ("?", {}))
                    key = name
                    if name == "Read": key = "Read:" + Path(str(inp.get("file_path", ""))).name
                    if name == "Skill": key = "Skill:" + str(inp.get("skill"))
                    tool_chars[key] += text_len(b.get("content"))
                    if name == "Agent":
                        for mm in AID.finditer(json.dumps(b.get("content"))):
                            children.append((mm.group(1), inp.get("subagent_type"), inp.get("description")))
    u = Counter()
    peak = 0
    for us in calls.values():
        ctx = us.get("input_tokens", 0) + us.get("cache_read_input_tokens", 0) + us.get("cache_creation_input_tokens", 0)
        peak = max(peak, ctx)
        u["input"] += us.get("input_tokens", 0); u["cache_read"] += us.get("cache_read_input_tokens", 0)
        u["cache_write"] += us.get("cache_creation_input_tokens", 0); u["output"] += us.get("output_tokens", 0)
    agents[aid] = dict(calls=len(calls), usage=dict(u), peak_ctx=peak, final_ctx=ctx if calls else 0,
                       tools=dict(tools), tool_chars=dict(tool_chars.most_common(12)),
                       children=children, prompt=(first_prompt or "")[:160], model=model,
                       start=min(ts) if ts else None, end=max(ts) if ts else None)

def processed(u): return u.get("input", 0) + u.get("cache_read", 0) + u.get("cache_write", 0) + u.get("output", 0)

result = {}
for rid, arm in ROOTS.items():
    rows = []
    def walk(aid, depth, stype, desc):
        a = agents.get(aid)
        if not a: rows.append(dict(id=aid, missing=True, depth=depth, type=stype, desc=desc)); return
        rows.append(dict(id=aid, depth=depth, type=stype or "ARM", desc=desc or arm, calls=a["calls"],
                         **a["usage"], processed=processed(a["usage"]), peak_ctx=a["peak_ctx"],
                         final_ctx=a["final_ctx"], tools=a["tools"], tool_chars=a["tool_chars"], model=a["model"]))
        seen = set()
        for cid, ct, cd in a["children"]:
            if cid in seen: continue
            seen.add(cid); walk(cid, depth + 1, ct, cd)
    walk(rid, 0, None, None)
    result[arm] = rows
OUT.write_text(json.dumps(result, indent=1))

for arm, rows in result.items():
    tot = Counter()
    for r in rows:
        for k in ("calls", "input", "cache_read", "cache_write", "output", "processed"): tot[k] += r.get(k, 0)
    root = rows[0]
    print(f"\n=== {arm}: {len(rows)} agents ({sum(1 for r in rows if r.get('missing'))} missing), {tot['calls']} API calls")
    print(f"  processed={tot['processed']:,} cache_read={tot['cache_read']:,} cache_write={tot['cache_write']:,} uncached_in={tot['input']:,} output={tot['output']:,}")
    print(f"  root: processed={root.get('processed',0):,} calls={root.get('calls')} peak_ctx={root.get('peak_ctx'):,} final_ctx={root.get('final_ctx'):,}")
    by = defaultdict(Counter)
    for r in rows[1:]:
        t = r.get("type") or "?"
        by[t]["n"] += 1; by[t]["processed"] += r.get("processed", 0); by[t]["output"] += r.get("output", 0); by[t]["calls"] += r.get("calls", 0)
    for t, c in sorted(by.items(), key=lambda x: -x[1]["processed"]):
        print(f"  {t:38} n={c['n']:3} calls={c['calls']:4} processed={c['processed']:>11,} output={c['output']:>8,}")
