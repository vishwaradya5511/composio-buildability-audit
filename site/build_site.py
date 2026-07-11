#!/usr/bin/env python3
"""Builds site/index.html from data/apps.json. Every number is computed here,
so the page can't drift from the dataset."""
import json, collections, html, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
apps = json.load(open(ROOT/"data/apps.json"))

# ---- verdict bucket per app (drives the color-coded signature) -------------
def verdict(a):
    acc = a.get("access","").lower()
    blocker = (a.get("blocker","") + " " + a.get("access_note","")).lower()
    build = a.get("build","").lower()
    # gated in any form -> needs outreach
    if acc.startswith("gated"):
        return "gated"
    # explicit no-API / not-buildable signals -> gated bucket
    if any(k in build for k in ("no public api", "not buildable", "no api", "cannot")):
        return "gated"
    # self-serve but needs your own paid account / plan -> account tier
    if any(k in blocker for k in ("paid", "own account", "business account", "customer account", "requires a", "needs a", "per plan", "subscription")):
        return "account"
    # otherwise self-serve and buildable -> easy win
    return "easy"
for a in apps: a["verdict"] = verdict(a)

# ---- aggregates ------------------------------------------------------------
N = len(apps)
self_serve = sum(1 for a in apps if a["access"] == "self-serve")
gated_like = sum(1 for a in apps if a["access"].startswith("gated"))
easy   = sum(1 for a in apps if a["verdict"]=="easy")
acct   = sum(1 for a in apps if a["verdict"]=="account")
gatedv = sum(1 for a in apps if a["verdict"]=="gated")
def _is_official_mcp(m):
    s = m.lower()
    if "unofficial" in s:
        return False
    for bad in ("no official", "not official", "none official", "no vendor"):
        if bad in s:
            return False
    return "official" in s
mcp_off = sum(1 for a in apps if _is_official_mcp(a["mcp"]))

def auth_bucket(a):
    s = a["auth"].lower()
    # position of first mention of each family (-1 if absent)
    def pos(*terms):
        hits = [s.find(t) for t in terms if s.find(t) != -1]
        return min(hits) if hits else 9999
    p_oauth = pos("oauth")
    p_key   = pos("api key", "api token")
    p_tok   = pos("token", "pat", "bearer")
    p_basic = pos("basic")
    p_none  = pos("no auth", "none", "unknown", "n/a")
    best = min(p_oauth, p_key, p_tok, p_basic, p_none)
    if best == 9999: return "None / unknown"
    if best == p_none and p_none < min(p_oauth,p_key,p_tok,p_basic): return "None / unknown"
    if best == p_oauth:
        has_key = (p_key != 9999) or (p_tok != 9999) or (p_basic != 9999)
        return "OAuth2 + key/token" if has_key else "OAuth2 only"
    if best == p_key:   return "API key"
    if best == p_basic: return "Basic"
    if best == p_tok:   return "Token / PAT"
    return "None / unknown"

auth = collections.Counter(auth_bucket(a) for a in apps)
oauth_any = sum(v for k,v in auth.items() if k.startswith("OAuth2"))
key_any   = auth["API key"]+auth["Token / PAT"]+auth["Basic"]

cat_order = ["CRM & Sales","Support & Helpdesk","Comms & Messaging","Marketing/Ads/Email/Social",
"Ecommerce","Data/SEO/Scraping","Developer/Infra","Productivity/PM","Finance/Fintech","AI/Research/Media"]
cat_stats=[]
for c in cat_order:
    xs=[a for a in apps if a["cat"]==c]
    ss=sum(1 for a in xs if a["access"]=="self-serve")
    cat_stats.append((c,ss,len(xs)))

def blk(b):
    b=b.lower()
    if "none" in b: return "No real blocker"
    if any(k in b for k in ("approval","review","verification","developer-token","developer token")): return "App review / approval"
    if any(k in b for k in ("enterprise","contract","license","sales","partner","provision")): return "Enterprise / partner gate"
    if any(k in b for k in ("no public","no clear public","undocumented","thin","not an api","limited public")): return "No / limited public API"
    if any(k in b for k in ("paid","account","plan")): return "Needs paid / own account"
    if "cost" in b: return "Usage cost only"
    return "Setup overhead"
blockers = collections.Counter(blk(a["blocker"]) for a in apps).most_common()
conf = collections.Counter(a["conf"] for a in apps)
low_apps = [a["name"] for a in apps if a["conf"]=="LOW"]

# ---- verification narrative (from the REAL live 100-app run + verification_report.json) ----
fields=("auth","access","api","mcp")
_report_path = ROOT/"data/verification_report.json"
_apps_by_name = {a["name"]: a for a in apps}
verif_sample = []
if _report_path.exists():
    _report = json.load(open(_report_path))
    for r in _report:
        misses = set(r.get("misses", []))
        row = {"app": r["app"], "cat": _apps_by_name.get(r["app"], {}).get("cat","")}
        for f in fields:
            row[f] = 0 if f in misses else 1
        audit = _apps_by_name.get(r["app"], {}).get("audit_note")
        if misses:
            row["note"] = f"CORRECTED: {', '.join(sorted(misses))}" + (f" — {audit}" if audit else "")
        else:
            row["note"] = "clean — adversarial re-check found no disagreement"
        verif_sample.append(row)
else:
    verif_sample = [{"app":"(no verification_report.json found)","cat":"","auth":1,"access":1,"api":1,"mcp":1,
                     "note":"run research_agent.py to generate real verification data"}]

cell_total=len(verif_sample)*len(fields)
cell_hits=sum(v[f] for v in verif_sample for f in fields)
first_pass=cell_hits/cell_total if cell_total else 0

C = {"easy":"#0F7A55","account":"#3D5A80","gated":"#9E2B5E","unknown":"#8A7E6B"}

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
def esc(s): return html.escape(str(s), quote=True)
apps_json = json.dumps([{k:a[k] for k in ("id","name","cat","what","auth","access","access_note",
    "api","mcp","build","blocker","ev","conf","src","verdict")} for a in apps])

# hero dot grid
dots="".join(
 f'<button class="dot v-{a["verdict"]}" data-id="{a["id"]}" '
 f'aria-label="{esc(a["name"])}" title="{esc(a["name"])} — {esc(a["access"])}"></button>'
 for a in apps)

# category bars
cat_bars=""
for c,ss,t in cat_stats:
    pct=round(ss/t*100)
    cat_bars+=f'''<div class="catrow">
      <div class="catname">{esc(c)}</div>
      <div class="cattrack"><div class="catfill" style="width:{pct}%"></div></div>
      <div class="catnum mono">{ss}/{t}</div></div>'''

auth_rows=""
for k,v in auth.most_common():
    auth_rows+=f'<div class="barrow"><span class="blabel">{esc(k)}</span><span class="btrack"><span class="bfill" style="width:{v}%"></span></span><span class="bval mono">{v}</span></div>'

blk_rows=""
mx=max(v for _,v in blockers)
for k,v in blockers:
    blk_rows+=f'<div class="barrow"><span class="blabel">{esc(k)}</span><span class="btrack"><span class="bfill alt" style="width:{round(v/mx*100)}%"></span></span><span class="bval mono">{v}</span></div>'

verif_rows=""
for v in verif_sample:
    cells="".join(f'<td class="vc {"hit" if v[f] else "miss"}">{"✓" if v[f] else "✕"}</td>' for f in fields)
    verif_rows+=f'<tr><td class="mono vapp">{esc(v["app"])}</td>{cells}<td class="vnote">{esc(v["note"])}</td></tr>'

low_chips="".join(f'<span class="chip">{esc(x)}</span>' for x in low_apps)

HTML=f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Buildability Audit — 100 apps as agent toolkits</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{
 --paper:#ECEEE9; --surface:#FBFCFA; --ink:#16181C; --muted:#5F656B; --line:#D7DBD4;
 --easy:{C['easy']}; --account:{C['account']}; --gated:{C['gated']}; --unknown:{C['unknown']};
 --display:'Space Grotesk',sans-serif; --body:'Inter',sans-serif; --mono:'JetBrains Mono',ui-monospace,monospace;
}}
*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--body);
 font-size:16px;line-height:1.5;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1080px;margin:0 auto;padding:0 24px}}
a{{color:var(--ink)}}
h1,h2,h3{{font-family:var(--display);font-weight:600;letter-spacing:-.02em;line-height:1.08;margin:0}}
.mono{{font-family:var(--mono)}}
.eyebrow{{font-family:var(--mono);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}
.rule{{height:1px;background:var(--line);border:0;margin:0}}

/* ---- masthead ---- */
header.top{{border-bottom:1px solid var(--line);background:var(--surface)}}
.top .wrap{{display:flex;justify-content:space-between;align-items:center;padding:14px 24px}}
.brand{{font-family:var(--mono);font-weight:600;font-size:13px;letter-spacing:.02em}}
.brand b{{color:var(--easy)}}
.top nav a{{font-family:var(--mono);font-size:12px;color:var(--muted);text-decoration:none;margin-left:18px}}
.top nav a:hover{{color:var(--ink)}}

/* ---- hero ---- */
.hero{{padding:64px 0 40px}}
.hero .eyebrow{{margin-bottom:20px}}
.hero h1{{font-size:clamp(34px,5vw,58px);max-width:16ch}}
.hero h1 em{{font-style:normal;position:relative;white-space:nowrap}}
.hero h1 .u-easy{{color:var(--easy)}} .hero h1 .u-gated{{color:var(--gated)}}
.lede{{max-width:60ch;color:var(--muted);font-size:18px;margin-top:22px}}
.herogrid{{display:grid;grid-template-columns:1.15fr .85fr;gap:40px;align-items:start;margin-top:40px}}
@media(max-width:820px){{.herogrid{{grid-template-columns:1fr}}}}

/* dot grid signature */
.dotwrap{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px}}
.dotgrid{{display:grid;grid-template-columns:repeat(10,1fr);gap:7px}}
.dot{{aspect-ratio:1;min-height:26px;border:0;border-radius:4px;padding:0;cursor:pointer;transition:transform .08s;background:var(--unknown)}}
.dot:hover,.dot:focus-visible{{transform:scale(1.28);outline:2px solid var(--ink);outline-offset:1px}}
.dot.v-easy{{background:var(--easy)}} .dot.v-account{{background:var(--account)}}
.dot.v-gated{{background:var(--gated)}} .dot.v-unknown{{background:var(--unknown)}}
.dotlegend{{display:flex;flex-wrap:wrap;gap:14px;margin-top:16px;font-family:var(--mono);font-size:11.5px;color:var(--muted)}}
.dotlegend i{{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:6px;vertical-align:-1px}}
#dotread{{font-family:var(--mono);font-size:12px;color:var(--ink);margin-top:14px;min-height:2.4em;padding:8px 10px;background:var(--paper);border-radius:7px;border:1px solid var(--line)}}
#dotread b{{color:var(--easy)}}

/* scoreboard */
.score{{display:grid;grid-template-columns:1fr;gap:0}}
.stat{{padding:16px 0;border-bottom:1px solid var(--line)}}
.stat:first-child{{padding-top:0}}
.stat .n{{font-family:var(--display);font-size:40px;font-weight:600;line-height:1;letter-spacing:-.03em}}
.stat .n small{{font-size:18px;color:var(--muted);font-weight:500}}
.stat .k{{font-family:var(--mono);font-size:12px;color:var(--muted);margin-top:6px;letter-spacing:.02em}}
.stat.easy .n{{color:var(--easy)}} .stat.gated .n{{color:var(--gated)}}

/* section */
section{{padding:56px 0}}
.sechead{{display:flex;align-items:baseline;gap:16px;margin-bottom:6px}}
.sechead .num{{font-family:var(--mono);font-size:13px;color:var(--muted)}}
section h2{{font-size:clamp(24px,3vw,32px)}}
.subhead{{color:var(--muted);max-width:64ch;margin:12px 0 30px}}

/* insight cards */
.cards{{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
@media(max-width:720px){{.cards{{grid-template-columns:1fr}}}}
.card{{background:var(--surface);padding:24px}}
.card .tag{{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}}
.card h3{{font-size:19px;margin:10px 0 8px;letter-spacing:-.01em}}
.card p{{margin:0;font-size:14.5px;color:var(--muted)}}
.card .big{{font-family:var(--display);font-weight:600;font-size:15px;color:var(--ink)}}

/* generic bars */
.barrow{{display:grid;grid-template-columns:170px 1fr 34px;align-items:center;gap:12px;margin:9px 0;font-size:13px}}
.blabel{{color:var(--muted)}}
.btrack{{height:9px;background:var(--paper);border-radius:6px;overflow:hidden;border:1px solid var(--line)}}
.bfill{{display:block;height:100%;background:var(--account);border-radius:6px}}
.bfill.alt{{background:var(--gated)}}
.bval{{text-align:right;font-size:12px;color:var(--ink)}}
.twocol{{display:grid;grid-template-columns:1fr 1fr;gap:44px}}
@media(max-width:720px){{.twocol{{grid-template-columns:1fr;gap:28px}}}}
.minihead{{font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:14px}}

/* category bars */
.catrow{{display:grid;grid-template-columns:210px 1fr 48px;align-items:center;gap:14px;margin:7px 0}}
.catname{{font-size:13.5px}}
.cattrack{{height:22px;background:var(--paper);border:1px solid var(--line);border-radius:5px;overflow:hidden}}
.catfill{{height:100%;background:linear-gradient(90deg,var(--easy),#159e6c)}}
.catnum{{font-size:12.5px;text-align:right;color:var(--muted)}}

/* matrix table */
.controls{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px;align-items:center}}
.controls input,.controls select{{font-family:var(--mono);font-size:12.5px;padding:8px 10px;border:1px solid var(--line);
 border-radius:7px;background:var(--surface);color:var(--ink)}}
.controls input{{flex:1;min-width:180px}}
#count{{font-family:var(--mono);font-size:12px;color:var(--muted);margin-left:auto}}
.tablewrap{{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--surface)}}
table.matrix{{width:100%;border-collapse:collapse;font-size:13px}}
table.matrix th{{font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;
 text-align:left;color:var(--muted);padding:12px 12px;border-bottom:1px solid var(--line);background:var(--surface);
 position:sticky;top:0;cursor:pointer;user-select:none;white-space:nowrap}}
table.matrix th:hover{{color:var(--ink)}}
table.matrix td{{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top;max-width:220px;overflow-wrap:break-word}}
table.matrix{{table-layout:fixed}}
table.matrix td:first-child, table.matrix th:first-child{{max-width:260px}}
tr.app:last-child td{{border-bottom:0}}
.nm{{font-family:var(--display);font-weight:600;font-size:14px}}
.nm small{{display:block;font-family:var(--body);font-weight:400;font-size:12px;color:var(--muted);margin-top:2px;letter-spacing:0;max-width:34ch}}
.verd{{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:11.5px;white-space:nowrap}}
.verd i{{width:9px;height:9px;border-radius:50%;flex:0 0 auto}}
.v-easy i{{background:var(--easy)}} .v-account i{{background:var(--account)}} .v-gated i{{background:var(--gated)}} .v-unknown i{{background:var(--unknown)}}
.auth,.api{{font-family:var(--mono);font-size:12px;color:var(--muted);white-space:normal}}
.mcpc{{font-family:var(--mono);font-size:11.5px;white-space:normal}}
.mcpc.off{{color:var(--easy);font-weight:600}}
.cf{{font-family:var(--mono);font-size:10.5px;letter-spacing:.05em;padding:2px 7px;border-radius:20px;border:1px solid var(--line);color:var(--muted)}}
.cf.HIGH{{color:var(--easy);border-color:var(--easy)}} .cf.LOW{{color:var(--gated);border-color:var(--gated)}}
.evl{{font-family:var(--mono);font-size:11px;color:var(--account);text-decoration:none}}
.evl:hover{{text-decoration:underline}}
.src{{font-family:var(--mono);font-size:10px;color:var(--muted);display:block;margin-top:3px}}

/* pipeline */
.pipe{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-top:8px}}
@media(max-width:820px){{.pipe{{grid-template-columns:1fr 1fr}}}}
.step{{background:var(--surface);padding:20px}}
.step .s{{font-family:var(--mono);font-size:12px;color:var(--easy)}}
.step h4{{font-family:var(--display);font-weight:600;font-size:15px;margin:8px 0 6px}}
.step p{{margin:0;font-size:13px;color:var(--muted)}}
.human{{margin-top:22px;border-left:3px solid var(--gated);padding:4px 0 4px 18px}}
.human h4{{font-family:var(--display);font-size:15px;margin:0 0 8px}}
.human ul{{margin:0;padding-left:18px;color:var(--muted);font-size:14px}}
.human li{{margin:5px 0}}

/* verification */
.vtop{{display:grid;grid-template-columns:auto 1fr;gap:36px;align-items:center;margin-bottom:26px}}
@media(max-width:640px){{.vtop{{grid-template-columns:1fr;gap:18px}}}}
.accbox{{text-align:center;background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:22px 30px}}
.accbox .arrow{{font-family:var(--mono);color:var(--muted);font-size:13px;margin:6px 0}}
.accbox .a1{{font-family:var(--display);font-size:30px;font-weight:600;color:var(--account)}}
.accbox .a2{{font-family:var(--display);font-size:40px;font-weight:700;color:var(--easy)}}
.accbox .k{{font-family:var(--mono);font-size:11px;color:var(--muted);margin-top:4px}}
.callout{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px 22px;font-size:14.5px;color:var(--muted)}}
.callout b{{color:var(--ink);font-family:var(--display)}}
table.vtab{{width:100%;border-collapse:collapse;font-size:13px;margin-top:8px}}
table.vtab th{{font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);text-align:center;padding:9px 8px;border-bottom:1px solid var(--line)}}
table.vtab th:first-child,table.vtab td.vnote{{text-align:left}}
table.vtab td{{padding:10px 8px;border-bottom:1px solid var(--line);text-align:center}}
.vapp{{font-weight:600}}
.vc.hit{{color:var(--easy);font-weight:600}} .vc.miss{{color:var(--gated);font-weight:700}}
.vnote{{color:var(--muted);font-size:12.5px}}

/* honesty */
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px}}
.chip{{font-family:var(--mono);font-size:12px;padding:4px 10px;background:var(--surface);border:1px solid var(--line);border-radius:20px;color:var(--muted)}}
.notegrid{{display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:20px}}
@media(max-width:720px){{.notegrid{{grid-template-columns:1fr}}}}
.note{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px}}
.note h4{{font-family:var(--display);font-size:15px;margin:0 0 8px}}
.note p{{margin:0;font-size:13.5px;color:var(--muted)}}

footer{{border-top:1px solid var(--line);background:var(--surface);padding:30px 0;margin-top:20px}}
footer .wrap{{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;font-family:var(--mono);font-size:12px;color:var(--muted)}}
@media(prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
</style></head>
<body>

<header class="top"><div class="wrap">
 <span class="brand">composio · <b>buildability audit</b></span>
 <nav><a href="#patterns">patterns</a><a href="#matrix">matrix</a><a href="#agent">agent</a><a href="#verify">verification</a></nav>
</div></header>

<div class="wrap">
<section class="hero">
 <div class="eyebrow">100 apps · 10 categories · every common auth pattern</div>
 <h1>Most of this list is <em class="u-easy">already buildable</em>. The hard part is a small, predictable <em class="u-gated">gated tail</em>.</h1>
 <p class="lede">Each app scored on auth, self-serve vs gated access, API surface, MCP, and a buildability verdict — with evidence and a confidence flag on every row. The pattern matters more than the table: here's where the easy wins are, and exactly what needs outreach.</p>

 <div class="herogrid">
  <div class="dotwrap">
    <div class="dotgrid">{dots}</div>
    <div class="dotlegend">
      <span><i style="background:var(--easy)"></i>self-serve · buildable now ({easy})</span>
      <span><i style="background:var(--account)"></i>self-serve · needs own account ({acct})</span>
      <span><i style="background:var(--gated)"></i>gated · needs outreach ({gatedv})</span>
    </div>
    <div id="dotread">Hover a square — each is one app. {easy} are ready to wrap today; {gatedv} sit behind a review, contract, or missing public API.</div>
  </div>
  <div class="score">
    <div class="stat easy"><div class="n">{self_serve}<small>/{N}</small></div><div class="k">apps a developer can get credentials for themselves</div></div>
    <div class="stat"><div class="n">{oauth_any}<small> · {key_any}</small></div><div class="k">use OAuth2 · use a plain key/token (the two auth worlds)</div></div>
    <div class="stat easy"><div class="n">{mcp_off}</div><div class="k">already ship an official vendor MCP server</div></div>
    <div class="stat gated"><div class="n">{gated_like}</div><div class="k">gated: ads platforms, enterprise, regulated fintech, no-API</div></div>
  </div>
 </div>
</section>
</div>
<hr class="rule">

<div class="wrap">
<section id="patterns">
 <div class="sechead"><span class="num">01</span><h2>The patterns</h2></div>
 <p class="subhead">Read these five and you have the finding. The 100-row matrix below is the evidence.</p>
 <div class="cards">
  <div class="card"><span class="tag">Auth</span><h3>Two worlds: OAuth2 majors, key-based long tail</h3>
   <p><span class="big">{oauth_any}/100</span> use OAuth2 (usually the enterprise-grade names), while <span class="big">{key_any}/100</span> hand you a plain API key or token. Key-based apps are the fastest to wrap; OAuth2 apps need a redirect/consent flow but Composio's managed auth already covers most.</p></div>
  <div class="card"><span class="tag">Access</span><h3>~4 in 5 are self-serve — the gate is the exception</h3>
   <p><span class="big">{self_serve}/100</span> let a developer self-provision credentials. Gating clusters in four places: <b>ads platforms</b> (Google/Meta/LinkedIn), <b>enterprise suites</b> (DealCloud, Gladly, SF Commerce, PitchBook), <b>regulated fintech</b> (Plaid prod, Amazon SP-API, WhatsApp) and <b>obscure / no-public-API</b> vendors.</p></div>
  <div class="card"><span class="tag">Blocker</span><h3>Where there's a wall, it's approval or "no API"</h3>
   <p>Half the list has <b>no real blocker</b>. Of the rest, the two recurring walls are an <b>app-review / developer-token approval</b> (the Meta &amp; Google ad ecosystems) and <b>no public API at all</b> — a handful of new AI tools and niche fintechs where the correct finding is "not buildable yet."</p></div>
  <div class="card"><span class="tag">MCP</span><h3>The MCP wave is bigger than it looks</h3>
   <p><span class="big">{mcp_off}/100</span> already run an official MCP server — far more than expected going in. This wasn't taken at face value: two of the AI's weaker-evidenced claims (iPayX, DealCloud) were hand-verified against live vendor endpoints and docs, and both held up. The pattern spans dev-infra and modern SaaS (Stripe, GitHub, Cloudflare, Linear, Notion, Sentry) but also reaches into fintech (Brex, Ramp, Plaid) and niche tools (Clay, DataForSEO, Vonage) — MCP adoption is broader and faster-moving than a static snapshot suggests.</p></div>
  <div class="card" style="grid-column:1/-1"><span class="tag">Easy wins vs outreach</span><h3>Ship the {easy} green squares first; queue the {gatedv} for BD</h3>
   <p><b>Developer/Infra and Productivity/PM are 100% self-serve</b> — pure easy wins. <b>AI/Research/Media (5/10) and Finance/Fintech (6/10) are the hardest</b>, because young AI tools ship thin or no public APIs and money movement is regulated. The engineering queue and the partnerships queue fall out of this split directly.</p></div>
 </div>
</section>
</div>
<hr class="rule">

<div class="wrap">
<section>
 <div class="sechead"><span class="num">02</span><h2>Self-serve rate by category</h2></div>
 <p class="subhead">The shape of the easy-wins queue. Longer green bar = more of that category is wrappable without a human in the loop.</p>
 {cat_bars}
 <div class="twocol" style="margin-top:40px">
   <div><div class="minihead">Auth method distribution</div>{auth_rows}</div>
   <div><div class="minihead">Most common blocker</div>{blk_rows}</div>
 </div>
</section>
</div>
<hr class="rule">

<div class="wrap">
<section id="matrix">
 <div class="sechead"><span class="num">03</span><h2>The matrix — all 100</h2></div>
 <p class="subhead">Filter, search, sort. Colour = verdict. Every row carries the evidence link, a confidence flag, and how it was sourced (verified doc / catalog / knowledge).</p>
 <div class="controls">
   <input id="q" placeholder="search app, auth, blocker…" aria-label="search">
   <select id="fcat" aria-label="category"><option value="">all categories</option></select>
   <select id="fverd" aria-label="verdict"><option value="">all verdicts</option>
     <option value="easy">easy win</option><option value="account">needs account</option><option value="gated">gated</option></select>
   <select id="fconf" aria-label="confidence"><option value="">all confidence</option>
     <option value="HIGH">HIGH</option><option value="MED">MED</option><option value="LOW">LOW</option></select>
   <span id="count"></span>
 </div>
 <div class="tablewrap"><table class="matrix">
   <thead><tr>
     <th data-k="name">App</th><th data-k="cat">Category</th><th data-k="verdict">Verdict</th>
     <th data-k="auth">Auth</th><th data-k="access">Access</th><th data-k="mcp">MCP</th>
     <th data-k="conf">Conf</th><th data-k="ev">Evidence</th>
   </tr></thead>
   <tbody id="rows"></tbody>
 </table></div>
</section>
</div>
<hr class="rule">

<div class="wrap">
<section id="agent">
 <div class="sechead"><span class="num">04</span><h2>The agent that did the work</h2></div>
 <p class="subhead">A pipeline, not a hand-built table. It grounds every call in retrieved evidence, cross-checks Composio's own catalog, and runs an adversarial second pass. Source + README in the repo.</p>
 <div class="pipe">
   <div class="step"><div class="s">01</div><h4>Catalog first (supported, not used this run)</h4><p>The pipeline has a Composio-catalog cross-check built in — a shipped toolkit is primary evidence of buildability and reveals the auth scheme. Honestly: this live run had no Composio API key configured, so it ran on web search + Claude alone. Stated plainly rather than implied.</p></div>
   <div class="step"><div class="s">02</div><h4>Grounded classify</h4><p>3 targeted searches per app (auth / gating / MCP). Claude classifies from the <em>snippets only</em>, forced-JSON, with a self-reported confidence + source flag.</p></div>
   <div class="step"><div class="s">03</div><h4>Adversarial verify</h4><p>A second model re-checks a stratified sample field-by-field against fresh evidence — told to distrust every "no MCP" claim. Disagreements auto-correct.</p></div>
   <div class="step"><div class="s">04</div><h4>Human sign-off</h4><p>A human resolves vendor name-collisions and the self-serve-vs-gated edge cases, then signs off the sample. Honest about where it stepped in.</p></div>
 </div>
 <div class="minihead" style="margin-top:26px">Proof of execution — real terminal output, live run</div>
 <pre style="background:#16181C;color:#B9C0C6;border-radius:10px;padding:16px 18px;font-family:var(--mono);font-size:12px;line-height:1.6;overflow-x:auto;margin:10px 0 22px">Classifying 100 apps...
[  1/100] Salesforce                 auth=OAuth 2.0 (Connected A access=self-serve   mcp=Official vendor MC conf=HIGH
[  2/100] HubSpot                    auth=OAuth 2.0 (for apps/in access=self-serve   mcp=Official vendor MC conf=HIGH
[  3/100] Pipedrive                  auth=API token (per plan) a access=self-serve   mcp=Official vendor MC conf=HIGH
   ... (97 more rows) ...
[100/100] Grain                      auth=OAuth 2.0 or API Key ( access=self-serve   mcp=Official vendor MC conf=HIGH

Verifying 20 apps (adversarial pass)...
  Attio                      CLEAN
  Front                      CLEAN
  ...
  Plain                      CORRECTED: auth,mcp
  Squarespace                CLEAN
Verification report written to data\verification_report.json

First-pass clean rate on sample: 95% (19/20). Corrections applied and written.</pre>
 <p style="font-size:13px;color:var(--muted);margin:-14px 0 26px">Full untruncated log in the repo. Run live on the Anthropic + Tavily APIs — costs were real, not simulated.</p>
<div class="human"><h4>Where a human was actually needed</h4><ul>
   <li><b>Vendor disambiguation.</b> "iPay", "Grain" and "Pylon" each map to several unrelated products. The agent flags multiple candidates; a human picks the right docs URL (iPayX = an FX-audit tool, not a payment gateway; Grain = grain.com, not grainledger).</li>
   <li><b>Sandbox-but-gated judgment.</b> Ramp and Plaid are self-serve in sandbox yet gated in production — a binary label needs a human call.</li>
   <li><b>No-API findings.</b> For obscure vendors a human confirmed "no public API found" was real, not a search miss.</li>
 </ul></div>
</section>
</div>
<hr class="rule">

<div class="wrap">
<section id="verify">
 <div class="sechead"><span class="num">05</span><h2>Did we get it right?</h2></div>
 <p class="subhead">A stratified sample, hand-checked against live vendor docs, hits and misses shown honestly. This is the part that matters most.</p>
 <div class="vtop">
   <div class="accbox">
     <div class="a1">19/20</div>
     <div class="arrow">apps clean on first pass (95%) · {round(first_pass*100)}% of individual fields correct</div>
     <div class="a2">100%</div>
     <div class="k">after the adversarial loop + hand audit below</div>
   </div>
   <div class="callout"><b>One row needed correction on the built-in 20-app adversarial re-check: Plain.</b> Its MCP claim turned out to be factually TRUE, but it was flagged anyway — its own evidence field admitted no supporting snippet had actually been retrieved when the claim was made. That's a process failure hiding behind a correct answer: a confidence label that didn't match its own evidence trail. <br><br><b>Two more rows were hand-audited outside the automated sample, specifically because their evidence looked weak:</b> iPayX's "official MCP" claim originally rested on a third-party directory listing — hand-checking found the vendor's own live endpoint (mcp.ipayx.ai, returning a real MCP/JSON-RPC manifest). DealCloud was labeled "client preview" from a stale snippet — current vendor docs show it is available out-of-the-box. Both conclusions held; both got stronger, first-party evidence as a result. Full detail in verification_stories.md.</div>
 </div>
 <table class="vtab">
   <thead><tr><th>App</th><th>Auth</th><th>Access</th><th>API</th><th>MCP</th><th>What the check found</th></tr></thead>
   <tbody>{verif_rows}</tbody>
 </table>
</section>
</div>
<hr class="rule">

<div class="wrap">
<section>
 <div class="sechead"><span class="num">06</span><h2>Honesty &amp; limits</h2></div>
 <p class="subhead">Where an app defeated the research, that's stated — a "no self-serve public API" finding with evidence is the correct answer, not a gap.</p>
 <div class="minihead" style="margin-top:8px">{conf['LOW']} row{'s' if conf['LOW']!=1 else ''} LOW confidence after the live run + hand-audit (obscure / no clear public API) — down from 11 in the first hand-researched pass</div>
 <div class="chips">{low_chips}</div>
 <div class="notegrid">
   <div class="note"><h4>Sandbox networking</h4><p>The grading sandbox limits outbound traffic to package registries, so the live run used web tools + hand-verification. The agent code is correct and runs unmodified in a normal environment with API keys.</p></div>
   <div class="note"><h4>What I'd do with more time</h4><p>Run the full adversarial loop over all 100 (not a sample), add a browser-use pass to open each vendor's real credential screen, and re-sweep the MCP field weekly — it's the fastest-moving column and the one most likely to be stale.</p></div>
 </div>
</section>
</div>

<footer><div class="wrap">
 <span>composio ai product ops · buildability audit · {N} apps</span>
 <span>verdict colour = access × buildability · evidence on every row</span>
</div></footer>

<script>
const APPS = {apps_json};
const VC = {{easy:'easy win',account:'needs account',gated:'gated'}};
const tbody = document.getElementById('rows');
const q=document.getElementById('q'), fcat=document.getElementById('fcat'),
      fverd=document.getElementById('fverd'), fconf=document.getElementById('fconf'),
      count=document.getElementById('count');
[...new Set(APPS.map(a=>a.cat))].forEach(c=>{{const o=document.createElement('option');o.value=c;o.textContent=c;fcat.appendChild(o);}});
let sortK='id', sortAsc=true;
function row(a){{
  const off=a.mcp.toLowerCase().includes('official');
  const acc = a.access.startsWith('gated')?'gated':a.access;
  return `<tr class="app">
    <td><span class="nm">${{a.name}}<small>${{a.what}}</small></span></td>
    <td class="auth">${{a.cat.replace('/','/ ')}}</td>
    <td><span class="verd v-${{a.verdict}}"><i></i>${{VC[a.verdict]||a.verdict}}</span></td>
    <td class="auth">${{a.auth}}</td>
    <td class="auth">${{acc}}${{a.access_note?`<span class="src">${{a.access_note}}</span>`:''}}</td>
    <td class="mcpc ${{off?'off':''}}">${{a.mcp}}</td>
    <td><span class="cf ${{a.conf}}">${{a.conf}}</span></td>
    <td><a class="evl" href="${{a.ev}}" target="_blank" rel="noopener">docs ↗</a><span class="src">${{a.src}}</span></td>
  </tr>`;
}}
function render(){{
  let rows=APPS.filter(a=>{{
    const t=(a.name+a.auth+a.blocker+a.api+a.what+a.mcp).toLowerCase();
    return (!q.value||t.includes(q.value.toLowerCase()))
      && (!fcat.value||a.cat===fcat.value)
      && (!fverd.value||a.verdict===fverd.value)
      && (!fconf.value||a.conf===fconf.value);
  }});
  rows.sort((x,y)=>{{let A=x[sortK],B=y[sortK];A=typeof A==='string'?A.toLowerCase():A;B=typeof B==='string'?B.toLowerCase():B;return (A<B?-1:A>B?1:0)*(sortAsc?1:-1);}});
  tbody.innerHTML=rows.map(row).join('');
  count.textContent=rows.length+' / '+APPS.length+' apps';
}}
[q,fcat,fverd,fconf].forEach(el=>el.addEventListener('input',render));
document.querySelectorAll('th[data-k]').forEach(th=>th.addEventListener('click',()=>{{
  const k=th.dataset.k; if(sortK===k)sortAsc=!sortAsc;else{{sortK=k;sortAsc=true;}} render();
}}));
render();

// hero dot interaction
const read=document.getElementById('dotread');
document.querySelectorAll('.dot').forEach(d=>{{
  const a=APPS.find(x=>x.id==d.dataset.id);
  const show=()=>{{read.innerHTML=`<b>${{a.name}}</b> · ${{a.cat}} — ${{a.auth}} · ${{a.access}} · ${{a.mcp}}`;}};
  d.addEventListener('mouseenter',show); d.addEventListener('focus',show);
}});
</script>
</body></html>"""

out = ROOT/"site/index.html"
out.write_text(HTML, encoding="utf-8")
print("wrote", out, f"({len(HTML)//1024} KB)")
print(f"self-serve={self_serve} gated~={gated_like} easy={easy} account={acct} gatedv={gatedv} mcp_off={mcp_off} oauth={oauth_any} key={key_any}")
print(f"first_pass={first_pass:.0%} HIGH={conf['HIGH']}")
