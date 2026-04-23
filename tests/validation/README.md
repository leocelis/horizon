# Validation Gate Tests (V1 / V2 / V3 / V5)

These tests implement the validation gates listed in `horizon_intent.yaml`:

| Gate | File                              | Requires                                                    |
|------|-----------------------------------|-------------------------------------------------------------|
| V1   | `test_v1_proxy.py`                | 200+ human-rated conversations across 3+ domains            |
| V2   | `test_v2_signal_quality.py`       | 300+ labeled turns per event type (4,200+ labels total)     |
| V3   | `test_v3_baseline.py`             | Same V1 corpus; implements heuristic baseline + benchmark  |
| V5   | `test_v5_generalization.py`       | 5+ held-out domains not represented in V1/V2                |

Each test file contains the real check logic. The tests auto-skip when the
required validation dataset is not available (set `HORIZON_VALIDATION_DATA`
env var to a directory containing the expected JSONL files to activate them).

These gates are authored per the intent so that they can be exercised as soon
as a validation corpus exists. They are the *product-validation* layer — not
the *implementation-correctness* layer covered by unit / integration tests.

## Dataset format expected

`HORIZON_VALIDATION_DATA/v1_rated_conversations.jsonl`
```
{"conversation_id": "...", "domain": "support", "turns": [{"human": "...", "agent": "...", "timestamp": "..."}], "human_rating": 0.73}
```

`HORIZON_VALIDATION_DATA/v2_labeled_events.jsonl`
```
{"conversation_id": "...", "turn": 3, "event_type": "signal.convergence", "label": true}
```

`HORIZON_VALIDATION_DATA/v5_heldout_conversations.jsonl`
(same schema as v1, but from domains disjoint with v1)
