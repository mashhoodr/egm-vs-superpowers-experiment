"""Model-aware $ cost per arm tree. Prices: claude-api skill model table (cached 2026-10-06).

usage: python3 -I price_runs.py SUBAGENT_DIR OUT_JSON label=rootid ...
Cache writes priced per TTL from usage.cache_creation (5m = 1.25x input, 1h = 2x input).
Haiku cache read assumed 0.1x input (not listed in the table). Output tokens are undercounted
in transcripts (usage logged before streaming ends), so totals are lower bounds.
"""
import json, re, sys
from pathlib import Path

PRICE = {  # $/MTok: input, output, cache_read
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}
SUB = Path(sys.argv[1]); OUT = Path(sys.argv[2])
ROOTS = dict(a.split("=") for a in sys.argv[3:])
AID = re.compile(r"agentId: ([0-9a-f]{17})")

def scan(aid):
    calls, kids, model = {}, [], None
    p = SUB / f"agent-{aid}.jsonl"
    if not p.exists(): return None
    for line in p.open():
        try: d = json.loads(line)
        except Exception: continue
        m = d.get("message")
        if not isinstance(m, dict): continue
        if m.get("role") == "assistant" and m.get("usage") and m.get("id"):
            calls[m["id"]] = (m.get("model"), m["usage"])
        c = m.get("content")
        if isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    kids += AID.findall(json.dumps(b.get("content")))
    return calls, list(dict.fromkeys(kids))

def cost(model, u):
    pi, po, pr = PRICE.get(model, PRICE["claude-opus-5-5"])
    cc = u.get("cache_creation") or {}
    w5, w1 = cc.get("ephemeral_5m_input_tokens"), cc.get("ephemeral_1h_input_tokens")
    if w5 is None and w1 is None: w5, w1 = u.get("cache_creation_input_tokens", 0), 0
    return (u.get("input_tokens", 0) * pi + (w5 or 0) * pi * 1.25 + (w1 or 0) * pi * 2.0
            + u.get("cache_read_input_tokens", 0) * pr + u.get("output_tokens", 0) * po) / 1e6

res = {}
for label, root in ROOTS.items():
    seen, stack, by_model, total, ntok = set(), [root], {}, 0.0, 0
    while stack:
        a = stack.pop()
        if a in seen: continue
        seen.add(a); s = scan(a)
        if not s: continue
        calls, kids = s; stack += kids
        for model, u in calls.values():
            c = cost(model, u); total += c
            by_model[model] = by_model.get(model, 0) + c
            ntok += sum(u.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens"))
    res[label] = dict(usd=round(total, 2), tokens=ntok, agents=len(seen), by_model={k: round(v, 2) for k, v in by_model.items()})
OUT.write_text(json.dumps(res, indent=1))
for k, v in res.items():
    print(f"{k:16} ${v['usd']:7.2f}  tokens={v['tokens']/1e6:6.1f}M  agents={v['agents']:3}  {v['by_model']}")
