"""
Horizon MCP Demo — Agent using MCP tools live.

The agent (this script) plays both sides of a developer conversation while
calling every MCP primitive at each turn, exactly as a Cursor / Claude agent
would.  Horizontal rule output shows the Horizon signals the agent reads and
acts on before composing its next reply.

Run:
    TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 PYTHONPATH=src python scripts/agent_demo_with_mcp.py
"""

import json
import os
import sys
import textwrap
from datetime import datetime, timedelta, timezone

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# ── MCP tool/resource functions (same code Cursor calls over stdio) ──────────
from horizon.mcp.server import (
    configure_session,
    get_events,
    get_trajectory,
    monitor_conversation,
    new_conversation,
    process_turn,
)

# ── helpers ──────────────────────────────────────────────────────────────────

W = 72

def banner(title: str) -> None:
    print("\n" + "═" * W)
    print(f"  {title}")
    print("═" * W)

def section(title: str) -> None:
    print(f"\n  ── {title}")

def line(label: str, value: object, indent: int = 4) -> None:
    pad = " " * indent
    print(f"{pad}{label:<30} {value}")

def wrap(text: str, indent: int = 6) -> None:
    prefix = " " * indent
    for para in text.strip().splitlines():
        for chunk in textwrap.wrap(para, W - indent) or [""]:
            print(prefix + chunk)

def horizon_panel(turn_result: dict) -> None:
    """Print the Horizon signals the agent reads before replying."""
    section("HORIZON SIGNALS  (agent reads before replying)")
    line("fidelity_score:", f"{turn_result['fidelity_score']:.3f}")
    line("health_status:", turn_result["health_status"])
    line("igt_value:", f"{turn_result['igt_value']:.3f}  (info gain this turn)")
    line("igt_trend:", f"{turn_result['igt_trend']:.4f}  (neg = converging)")
    line("divergence_score:", f"{turn_result['divergence_score']:.3f}")
    line("consistency_score:", f"{turn_result['consistency_score']:.3f}")
    if turn_result.get("gap_seconds") is not None:
        line("gap:", f"{turn_result['gap_seconds']:.0f}s  [{turn_result['gap_class']}]")
    if turn_result.get("estimated_retention") is not None:
        line("estimated_retention:", f"{turn_result['estimated_retention']:.2%}")
    if turn_result.get("circadian_factor") is not None:
        line("circadian_factor:", f"{turn_result['circadian_factor']:.3f}")
    if turn_result.get("interval_class") is not None:
        line("spacetime interval:", f"ds²={turn_result['spacetime_interval']:.3f}  [{turn_result['interval_class']}]")
    if turn_result.get("spatial_constraint"):
        sc = turn_result["spatial_constraint"]
        line("spatial_constraint:", f"screen={sc['screen_capacity']}  attn={sc['attention_budget']}  max_tokens={sc['max_response_length']}")

    active = [e for e in turn_result["events"] if e["active"]]
    all_ev = turn_result["events"]
    if all_ev:
        print(f"    {'events fired:':<30} {len(all_ev)} total, {len(active)} active")
        for ev in all_ev:
            flag = "🔴 ACTIVE" if ev["active"] else "○ observe"
            print(f"      [{flag}] {ev['type']:<35}  conf={ev['confidence']:.2f}")
            if ev["active"]:
                print(f"              → {ev['suggested_behavior']}")
    else:
        line("events fired:", "none")

def resource_panel(sid: str, turn_n: int) -> None:
    """Read and display trajectory + events resources (agent context injection)."""
    section(f"RESOURCES  (agent reads horizon://session/…  before turn {turn_n})")
    traj = json.loads(get_trajectory(session_id=sid))
    evts = json.loads(get_events(session_id=sid))
    line("trajectory.turn_count:", traj["turn_count"])
    line("trajectory.health:", traj["health_status"])
    line("trajectory.scores:", [round(s, 3) for s in traj["scores"]])
    line("trajectory.igt_trend:", round(traj["igt_trend"], 4))
    if traj.get("estimated_t_star"):
        line("trajectory.t_star:", traj["estimated_t_star"])
    line("events.active:", evts["active_count"])
    line("events.total:", evts["total_count"])
    if evts["active_events"]:
        for ae in evts["active_events"]:
            print(f"      ⚠  {ae['type']}  → {ae['suggested_behavior']}")

def agent_action(action: str) -> None:
    """Show what the agent decides to do based on Horizon signals."""
    print(f"\n  ▶ AGENT ACTION:  {action}")


# ═════════════════════════════════════════════════════════════════════════════
# THE CONVERSATION
# ═════════════════════════════════════════════════════════════════════════════

banner("HORIZON MCP SERVER — LIVE AGENT DEMO")
print()
print("  The agent is a developer-assistant helping a user build a distributed")
print("  rate-limiter.  At every turn the agent calls the Horizon MCP tools and")
print("  reads the resources before composing its reply — exactly as Cursor does.")
print()
print("  MCP primitives used in this demo:")
print("    Tool     new_conversation     — start session")
print("    Prompt   monitor_conversation — inject agent loop + instructions")
print("    Tool     process_turn         — record every turn, get signals")
print("    Resource trajectory           — read fidelity arc before each reply")
print("    Resource events              — check active alerts before each reply")
print("    Tool     configure_session    — tune threshold mid-conversation")

# ── STEP 0: Prompt invocation  (user types /monitor_conversation) ─────────
banner("STEP 0 — /monitor_conversation  (user invokes the MCP Prompt)")
prompt_text = monitor_conversation(domain="technical", agent_name="cursor-agent")
# Extract the session_id the prompt embedded
sid = None
for line_text in prompt_text.splitlines():
    if "session_id" in line_text and ":" in line_text:
        candidate = line_text.split(":")[-1].strip()
        if len(candidate) == 36:
            sid = candidate
            break
print(f"\n  Prompt created session:  {sid}")
print("  Agent loop injected into context.  First 400 chars of prompt:")
wrap(prompt_text[:400] + "…", indent=4)

# Base timestamp: 10 AM on a Tuesday (cognitive peak)
base = datetime(2026, 5, 6, 10, 0, 0, tzinfo=timezone.utc)
client_ctx = {"device_type": "laptop", "timezone": "America/New_York"}

# ─────────────────────────────────────────────────────────────────────────────
# TURN 1  — user asks the opening question
# ─────────────────────────────────────────────────────────────────────────────
banner("TURN 1 — User opens the conversation")

human_1 = (
    "I'm building a distributed rate-limiter in Go. "
    "I want it to work across multiple nodes without a central coordinator. "
    "What algorithm would you recommend and why?"
)
agent_1 = (
    "For a coordinator-free distributed rate-limiter I'd recommend the "
    "**Token Bucket with gossip-based synchronisation** (CRDT-style). Each node "
    "maintains its own token bucket and periodically gossips its consumed-token "
    "count to peers. You merge with a max-register CRDT so you never undercount "
    "consumption. Alternatives: GCRA (Generic Cell Rate Algorithm) is simpler but "
    "needs a shared clock; Sliding Window Log requires too much state to replicate. "
    "Token Bucket + gossip gives you ~eventual consistency with bounded error "
    "proportional to the gossip interval — typically < 5% over-spend at 100ms sync."
)

print(f"\n  USER:  {human_1[:80]}…")
print(f"  AGENT: {agent_1[:80]}…")

t1 = base
r1 = process_turn(
    session_id=sid,
    human_message=human_1,
    agent_response=agent_1,
    timestamp=t1.isoformat(),
    client_context=client_ctx,
)
horizon_panel(r1)
agent_action("Conversation is healthy, high IGT (novel domain opened). Reply in full.")

# ─────────────────────────────────────────────────────────────────────────────
# TURN 2  — 4 minutes later, follow-up
# ─────────────────────────────────────────────────────────────────────────────
banner("TURN 2 — Follow-up (4 min gap)")

human_2 = (
    "How do I handle the clock skew between nodes? "
    "If one node's clock is 200ms behind, won't it allow extra requests?"
)
agent_2 = (
    "Clock skew is the main failure mode. Fix it with two mechanisms: "
    "1. **Logical clocks** — use Lamport timestamps instead of wall clocks for "
    "the gossip vector; only physical time matters for the bucket refill rate. "
    "2. **Skew-tolerant refill** — add a `skew_budget` parameter (e.g. 200ms). "
    "When refilling, subtract `min(elapsed, elapsed - skew_budget)` so a lagging "
    "node never over-refills. In practice, with NTP drift < 50ms and a 100ms gossip "
    "interval the error is negligible for most rate-limit SLAs."
)

print(f"\n  USER:  {human_2[:80]}…")
print(f"  AGENT: {agent_2[:80]}…")

t2 = base + timedelta(minutes=4)
r2 = process_turn(
    session_id=sid,
    human_message=human_2,
    agent_response=agent_2,
    timestamp=t2.isoformat(),
    client_context=client_ctx,
)
horizon_panel(r2)
resource_panel(sid, turn_n=3)
agent_action("Still healthy, good IGT. Gap is 'minutes' — retention near 100%. Continue depth.")

# ─────────────────────────────────────────────────────────────────────────────
# TURN 3  — 2 min gap, gets into implementation
# ─────────────────────────────────────────────────────────────────────────────
banner("TURN 3 — Implementation question (2 min gap)")

human_3 = (
    "Can you show me the core data structure in Go? "
    "Just the bucket struct and the refill logic."
)
agent_3 = """\
```go
type TokenBucket struct {
    mu          sync.Mutex
    tokens      float64   // current token count
    capacity    float64   // max tokens
    refillRate  float64   // tokens/second
    lastRefill  time.Time
    consumed    float64   // monotonic counter for gossip
}

func (b *TokenBucket) Refill(skewBudget time.Duration) {
    b.mu.Lock()
    defer b.mu.Unlock()
    now := time.Now()
    elapsed := now.Sub(b.lastRefill).Seconds()
    // Apply skew budget so lagging nodes never over-refill
    if skewBudget > 0 {
        elapsed = math.Max(0, elapsed-skewBudget.Seconds())
    }
    b.tokens = math.Min(b.capacity, b.tokens+elapsed*b.refillRate)
    b.lastRefill = now
}

func (b *TokenBucket) Allow(n float64) bool {
    b.mu.Lock()
    defer b.mu.Unlock()
    b.Refill(0)
    if b.tokens >= n {
        b.tokens -= n
        b.consumed += n
        return true
    }
    return false
}
```"""

print(f"\n  USER:  {human_3[:80]}…")
print(f"  AGENT: (Go struct + Refill + Allow — 30 lines of code)")

t3 = base + timedelta(minutes=6)
r3 = process_turn(
    session_id=sid,
    human_message=human_3,
    agent_response=agent_3,
    timestamp=t3.isoformat(),
    client_context=client_ctx,
)
horizon_panel(r3)
agent_action("Code response delivered. Monitoring for clarification checkpoint.")

# ─────────────────────────────────────────────────────────────────────────────
# TURN 4  — 90-MINUTE GAP  (user went to a meeting)
# ─────────────────────────────────────────────────────────────────────────────
banner("TURN 4 — USER RETURNS AFTER 90-MINUTE GAP  ⏰")

human_4 = (
    "Ok back. So I was thinking — should the gossip also include "
    "the current token count, or just the consumed counter?"
)
agent_4 = (
    "Gossip only the **consumed counter** (monotonic), never the token count. "
    "Token count is derived: `tokens = capacity - consumed_since_last_refill`. "
    "Gossiping token count introduces a race: if two nodes compute it at different "
    "wall-clock moments you get a non-monotonic merge, which can *increase* apparent "
    "availability (the exact bug you're trying to prevent). The consumed counter is "
    "monotonically increasing, so CRDT max-merge is safe. On receipt, each node "
    "recomputes its local token count: `local_tokens = capacity - max(local_consumed, "
    "peer_consumed) + refill_since_last_gossip`."
)

print(f"\n  USER:  {human_4[:80]}…")
print(f"  AGENT: {agent_4[:80]}…")

t4 = base + timedelta(minutes=96)  # 90-min gap
r4 = process_turn(
    session_id=sid,
    human_message=human_4,
    agent_response=agent_4,
    timestamp=t4.isoformat(),
    client_context=client_ctx,
)
horizon_panel(r4)
resource_panel(sid, turn_n=5)

# Show the agent acting on temporal signals
if r4.get("gap_seconds", 0) > 3000:
    agent_action(
        f"90-min gap detected (gap_class='{r4['gap_class']}', "
        f"retention={r4['estimated_retention']:.0%}). "
        "Horizon says memory decayed — agent adds a quick recap in reply."
    )
    print()
    print("  ┌─ AGENT RECAP injected (triggered by Horizon temporal signal) ─────")
    print("  │  'Quick recap before we continue: we settled on Token Bucket +")
    print("  │  gossip-sync with a skew_budget param and CRDT max-merge on the")
    print("  │  consumed counter. Now, on your question about what to gossip…'")
    print("  └───────────────────────────────────────────────────────────────────")

# ─────────────────────────────────────────────────────────────────────────────
# TURN 5  — configure_session  (agent notices clarification threshold)
# ─────────────────────────────────────────────────────────────────────────────
banner("TURN 5 — Agent tunes config mid-conversation")

print("  Agent calls configure_session to tighten clarification threshold")
print("  for this technical deep-dive (default 0.35 is too loose):")
cfg = configure_session(session_id=sid, clarification_threshold=0.15, domain="technical")
print(f"  applied: {cfg['applied']}")
print(f"  warnings: {cfg['warnings']}")

human_5 = (
    "Makes sense. One more thing — how do I test this locally without "
    "spinning up multiple actual nodes?"
)
agent_5 = (
    "Use **in-process goroutines with a simulated network delay**. Create N "
    "TokenBucket instances, each in its own goroutine, connected by buffered channels "
    "that add `time.Sleep(gossipLatency)` before delivering messages. This replicates "
    "the gossip timing without Docker/k8s overhead. For the clock skew test, inject a "
    "`clockOffset` parameter per bucket and verify that total requests allowed across "
    "N buckets stays within `rateLimit * (1 + skewBudget/gossipInterval)` tolerance. "
    "Write a table-driven test with skew=0ms, 50ms, 200ms and confirm the invariant holds."
)

print(f"\n  USER:  {human_5[:80]}…")
print(f"  AGENT: {agent_5[:80]}…")

t5 = base + timedelta(minutes=100)
r5 = process_turn(
    session_id=sid,
    human_message=human_5,
    agent_response=agent_5,
    timestamp=t5.isoformat(),
    client_context=client_ctx,
)
horizon_panel(r5)
agent_action("No active alerts. Conversation healthy. Continue.")

# ─────────────────────────────────────────────────────────────────────────────
# TURN 6  — Convergence: user signals they're done
# ─────────────────────────────────────────────────────────────────────────────
banner("TURN 6 — Natural convergence")

human_6 = "This is exactly what I needed. Thanks — I think I have everything to implement it."
agent_6 = (
    "Great! To summarise what we landed on: Token Bucket with gossip-based CRDT sync, "
    "consumed-counter-only gossip (monotonic, safe for max-merge), skew_budget param "
    "to absorb NTP drift, and goroutine-based local test harness. "
    "If you hit issues with hot partitions (one node receiving disproportionate traffic) "
    "the next step is weighted gossip — happy to pick that up if needed."
)

print(f"\n  USER:  {human_6}")
print(f"  AGENT: {agent_6[:80]}…")

t6 = base + timedelta(minutes=103)
r6 = process_turn(
    session_id=sid,
    human_message=human_6,
    agent_response=agent_6,
    timestamp=t6.isoformat(),
    client_context=client_ctx,
)
horizon_panel(r6)

if r6["health_status"] in ("converged", "healthy"):
    agent_action(
        f"health='{r6['health_status']}', IGT trend={r6['igt_trend']:.4f}. "
        "Conversation reached natural closure. Agent wraps up with summary."
    )

# ─────────────────────────────────────────────────────────────────────────────
# FINAL RESOURCE READ — full trajectory + event log
# ─────────────────────────────────────────────────────────────────────────────
banner("FINAL — Agent reads full trajectory + event log before closing")

traj = json.loads(get_trajectory(session_id=sid))
evts = json.loads(get_events(session_id=sid))

section("TRAJECTORY  (horizon://session/{sid}/trajectory)")
line("session_id:", traj["session_id"][:8] + "…")
line("turn_count:", traj["turn_count"])
line("health_status:", traj["health_status"])
line("peak_fidelity:", f"{traj['peak_fidelity']:.3f}")
line("current_fidelity:", f"{traj['current_fidelity']:.3f}")
line("igt_trend:", f"{traj['igt_trend']:.4f}")
if traj.get("estimated_t_star"):
    line("estimated_t_star:", traj["estimated_t_star"])
print(f"    {'scores (per turn):':<30}", end=" ")
print([round(s, 3) for s in traj["scores"]])
print(f"    {'gap_durations (s):':<30}", end=" ")
print(traj["gap_durations"])

section("EVENTS  (horizon://session/{sid}/events)")
line("total events:", evts["total_count"])
line("active events:", evts["active_count"])
if evts["all_events"]:
    for ev in evts["all_events"]:
        flag = "● ACTIVE" if ev["active"] else "○"
        print(f"      {flag}  turn={ev['turn']}  {ev['type']:<35}  conf={ev['confidence']:.2f}")

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
banner("SUMMARY — What Horizon contributed to this conversation")

print("""
  Turn  1  new conversation opened, high IGT (novel domain)
           → agent gave full comprehensive answer
  Turn  2  4-min gap, 'minutes' class, retention ≈ 100%
           → agent continued depth without recapping
  Turn  4  90-MIN GAP detected (signal.temporal_desync fires if enabled)
           → agent injected a context recap before answering
           → WITHOUT Horizon: agent would have answered as if no gap occurred
  Turn  5  agent called configure_session mid-conversation
           → tightened clarification threshold for technical domain
  Turn  6  natural convergence (IGT trend → 0)
           → agent wrapped with summary instead of opening new topics

  All 6 turns processed via MCP tools + resources in-process.
  The same code runs over stdio when Cursor connects to the server.
""")
