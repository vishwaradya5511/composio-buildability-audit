# Composio AI Product Ops — 100-App Buildability Research

Research pipeline that classifies 100 apps on whether each could be an **agent
toolkit today** — auth method, self-serve vs gated, API surface + MCP,
buildability verdict, and evidence — then finds the **patterns** across all 100
and **verifies its own accuracy** with an adversarial loop plus human checks.

**Live page:** https://magenta-gnome-59538d.netlify.app/
**Deliverable in this repo:** `site/index.html` — same page, self-contained
(open it in a browser; no build step, no server).

---

## What's in here
## How the agent works

1. **Composio catalog first (built in, not exercised this run).** The pipeline
   supports asking Composio's own catalog whether a toolkit already exists —
   a shipped toolkit is primary evidence of buildability and reveals the auth
   scheme. Honestly: this live run had no `COMPOSIO_API_KEY` configured, so it
   ran on web search + Claude alone. Confirmed by checking `apps.json`: 0 rows
   are sourced from the catalog.
2. **Grounded classification.** 3 targeted web searches per app (auth / gating /
   MCP) via Tavily. Claude classifies from the retrieved snippets only — not
   from memory — with a forced-JSON schema and a self-reported confidence +
   source flag.
3. **Adversarial verification loop.** A second model re-checks a 20-app
   stratified sample field-by-field against fresh evidence, explicitly told to
   distrust any "no MCP" claim. Disagreements are auto-corrected.

## Where a human was needed (honest)

- **Vendor disambiguation.** Several names collide (`iPay*`, `Grain*`,
  `Pylon*`). The agent flags multiple candidates; a human picks the correct
  docs URL (e.g. iPayX = an FX-audit tool, not a payment gateway).
- **Gated-but-has-sandbox judgment.** Ramp and Plaid are self-serve in sandbox
  but gated in production. A human sets the final `access` label.
- **Hand-audit beyond the automated sample.** Two rows outside the 20-app
  sample were pulled aside because their evidence looked weak, and checked by
  hand against live vendor endpoints — see `verification_stories.md`.

## Run it yourself

```bash
pip install anthropic requests composio      # composio optional
export ANTHROPIC_API_KEY=sk-...
export TAVILY_API_KEY=...                     # or SERPER_API_KEY
export COMPOSIO_API_KEY=...                   # optional catalog cross-check

cd agent
python research_agent.py --apps ../data/apps_input.json --out ../data/apps.json --verify-sample 15
```

Outputs `data/apps.json` and `data/verification_report.json`. Rebuild the page
with `python site/build_site.py`.

## Verification — the part that matters most

Built-in adversarial pass on a 20-app stratified sample:
**19/20 apps clean on first pass (95%)**, **98% of individual fields correct.**

The one correction (**Plain**) is the most important finding on the whole
page: the agent's MCP claim was factually **true**, but its own evidence field
admitted no supporting snippet had actually been retrieved when the claim was
made — a confidence label that didn't match its own evidence trail. Right
answer, ungrounded process.

Two more rows were hand-audited **outside** the automated sample, specifically
because their evidence looked weak:
- **iPayX** — originally cited only a third-party MCP directory listing.
  Hand-check found the vendor's own live endpoint (`mcp.ipayx.ai`), which
  returns a real MCP/JSON-RPC manifest. Same conclusion, stronger evidence.
- **DealCloud** — labeled "client preview" from a stale snippet. Current
  vendor docs show the MCP server is available out-of-the-box. Upgraded from
  preview to generally-available.

Full detail on all four verification stories (including Attio's gated-vs-self-serve
nuance) in `verification_stories.md` and `audit_findings.md`.

## Headline numbers (computed from `data/apps.json`, not hand-typed)

- **78/100** apps are self-serve.
- **62/100** already ship an official vendor MCP server — two of the weakest
  claims (iPayX, DealCloud) were independently hand-verified and held up.
- **39/100** use OAuth2 as primary auth; **58/100** use a plain API key/token.
- **1 row** is LOW confidence (`Paygent Connect` — no public API docs found).
  Down from 11 in an earlier, purely-hand-researched pass, because the live
  run surfaced first-party evidence (e.g. `mcp.ipayx.ai`) that the manual pass
  hadn't found.

## Honesty / limitations

- The original development sandbox restricted outbound network to package
  registries; research there was done via web tools + hand-verification. The
  agent code itself was later run for real (paid, live) against the Anthropic
  and Tavily APIs — see the "Proof of execution" section on the live page for
  actual terminal output from that run.
- Composio's SDK/catalog cross-check is implemented in `research_agent.py` but
  was not exercised in the live run (no API key configured) — stated plainly
  rather than implied.
- MCP is the fastest-moving field in this dataset and the most likely to be
  stale by the time this is read — worth re-checking closest to any real
  decision.
