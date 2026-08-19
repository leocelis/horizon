# Examples

Runnable end-to-end scripts showing Horizon wired into different agent
frameworks.

## Setup

```bash
pip install -e .                          # horizon-monitor itself, from the repo root
pip install -r examples/requirements.txt   # dotenv + the framework SDKs used below
```

## Zero-key starting point

[`raw_framework_agnostic_e2e.py`](raw_framework_agnostic_e2e.py) runs fully
offline — no API key, no framework SDK, nothing beyond `horizon-monitor`
and the stdlib. Start here:

```bash
python examples/raw_framework_agnostic_e2e.py
```

## Everything else needs an API key

The remaining examples call a real model and load credentials from a
`.env` file (or the environment) via `python-dotenv`:

| Example | Needs |
|---|---|
| `openai_real_agent_e2e.py` | `OPENAI_API_KEY` |
| `openai_agents_sdk_e2e.py` | `OPENAI_API_KEY` |
| `langchain_real_agent_e2e.py` | `OPENAI_API_KEY` |
| `anthropic_real_agent_e2e.py` | `ANTHROPIC_API_KEY` |

Create a `.env` file in the repo root (or export the variable directly)
before running any of them, e.g.:

```bash
echo "OPENAI_API_KEY=sk-..." >> .env
python examples/openai_real_agent_e2e.py
```

## `memento_mori_mission_clock.py` — the mission plane

Runs with no arguments, no network, no API key and no LLM call. Builds a small synthetic
mission in a temporary store, evaluates the clock at a fixed instant, and prints what an
operator sees: ages, an expired task lifespan, an overdue park, the slowest entity beside
the entity currently blocking, the refusal of an undated park, one edge-triggered signal
under the per-turn cap, and proof that removing the declared rate leaves every
non-monetary field identical.

```bash
python examples/memento_mori_mission_clock.py
```
