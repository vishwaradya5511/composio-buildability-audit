# Verification Stories - the four rows worth talking about

Core lesson: in all four cases the agent's ANSWER was correct, but the QUALITY
of its reasoning/evidence varied. Verification was about checking the PATH to the
answer, not just the answer itself.

## 1. Plain - right answer, ungrounded process  (caught in 20-app adversarial pass)
The agent claimed an official Plain MCP with HIGH / verified-doc confidence, while
its own evidence field admitted no supporting snippet had been retrieved. The claim
was independently confirmed TRUE (mcp.plain.com). But the confidence label was earned
by luck, not process - the same failure on a less-documented app could produce a
confident WRONG answer. This is the most important class of bug to surface honestly.

## 2. Attio - "gated vs self-serve" is not binary  (hand-audited)
Agent said "gated"; earlier manual pass said "self-serve". Both partly right: a free
trial workspace is self-serve, but a real developer/sandbox workspace needs emailing
support@attio.com and ~2-day manual approval. The agent captured this nuance more
precisely than the human first pass. Suggests a 3-state label: self-serve /
trial-only / gated.

## 3. iPayX - right answer, weak evidence -> upgraded  (hand-verified live)
Agent cited only a community directory (chat.mcp.so) as proof of an official MCP.
Hand-check found the vendor's OWN live endpoint: https://mcp.ipayx.ai/mcp returns a
live MCP/JSON-RPC 2.0 manifest (4 tools, deployed 2026-07-10, docs at ipayx.ai/developers).
Same conclusion, far stronger evidence.

## 4. DealCloud - stale "preview" label -> upgraded  (hand-verified docs)
Agent labeled it "client preview" from an old snippet. Current official docs
(api.docs.dealcloud.com) show a default MCP server available out-of-the-box, plus
admin-configurable custom MCP servers scoped by Schema Contracts. Upgraded from
"preview" to "generally available".

## The one-liner for the interview
"The agent was accurate on conclusions, but its evidence quality was uneven - so I
built verification around auditing the reasoning path, not just spot-checking answers.
That caught a right-answer-wrong-process case (Plain), a false binary (Attio), and two
correct-but-weakly-evidenced claims I upgraded with first-party proof (iPayX, DealCloud)."
