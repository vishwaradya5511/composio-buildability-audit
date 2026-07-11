# Audit Findings — Two Flagged Rows (for report + interview)

These two rows were pulled aside during manual spot-checking of the 100-app
live run, on top of the built-in 20-app adversarial verification pass. Neither
was part of the automated sample; both were investigated by hand.

## 1. Attio — "gated" vs "self-serve" (resolved: label is correct, more precise than earlier)

- **Live-run label:** `access: gated`
- **Earlier manual research (Action 4 of original log):** listed Attio as self-serve
- **Resolution:** not a contradiction — a genuine nuance. A free trial workspace
  is self-serve, but a real developer/sandbox workspace requires emailing
  support@attio.com and waiting ~2 days for manual approval. The live-run
  agent's evidence (docs.attio.com/rest-api/guides/authentication,
  docs.attio.com/mcp/overview, a Stacksync how-to guide, and a GitHub MCP repo)
  captured this nuance more precisely than the original manual pass did.
- **Takeaway for report:** "gated vs self-serve" is not always binary — some
  vendors have a fast free tier AND a gated production tier. Worth a
  three-state label (self-serve / self-serve-trial-only / gated) in a v2.

## 2. Plain — MCP claim was TRUE, but asserted without grounded evidence (process failure)

- **Live-run label:** `mcp: Official Plain MCP server exists`, `conf: HIGH`,
  `src: verified-doc`, citing https://www.plain.com/blog/mcp-customer-support-2026
- **Problem noticed:** the row's own `ev` (evidence) field stated
  *"search snippets do not contain Plain-specific auth or MCP details"* —
  i.e. the model asserted a HIGH-confidence, verified-doc claim while its own
  logged evidence admitted it had nothing to back it up at generation time.
- **Independent re-verification:** the URL is real and live. Plain does ship
  an official MCP server (mcp.plain.com, ~30 tools, OAuth-based, read+write,
  covering threads/customers/tenants/help-center), confirmed via Plain's own
  help center (help.plain.com/article/mcp-server) and changelog
  (plain.com/changelog/plain-mcp) — independent of the originally-cited blog.
- **Verdict: the fact was correct, but the confidence label was earned by
  luck, not by process.** This is the more important class of bug to report
  honestly: a model can state a true fact with a HIGH/verified-doc label while
  its own retrieval step failed — meaning the SAME failure mode on a
  less-documented, less-guessable app could just as easily produce a
  confident, wrong answer instead. The 95% first-pass accuracy stat is real,
  but it doesn't capture this "right answer, ungrounded reasoning" case,
  because the sampled verifier marked it CLEAN based on a fresh search that
  happened to find real evidence this time.

## Why these two are worth raising unprompted in the interview

- Shows the review process didn't stop at the built-in 20-sample check —
  extra manual due diligence was applied to catch a subtler failure mode
  (confidence/evidence mismatch) that automated sampling wouldn't surface
  unless it happened to land on this exact row.
- Demonstrates the difference between "the answer was right" and "the
  process that produced the answer was sound" — the second is the harder,
  more valuable thing to evaluate, and is exactly what a real research-ops
  role would need to catch before shipping a toolkit based on this data.
