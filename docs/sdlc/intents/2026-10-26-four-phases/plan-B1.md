# Plan B1: phases in state.py, contract v2, stricter changes pass the trust anchor

Spec: [spec.md](spec.md) · FR-01, FR-02, FR-10 · ACs 1, 2, 3

1. `scripts/state.py`: stage names 1 Define, 4 Build, 5 Prove, 8 Ship (old names kept for 2, 3, 6, 7, 9–11); snapshot `phase`; `CONTRACT_VERSION = 2`. Test: test_state › test_advancing_a_stage_… (updated), test_a_feature_started_under_the_eleven_stages_moves_on_to_ship (new).
2. `hooks/trust_anchor.py`: Track up, Risk low → high, Flow lite → full become the new anchor without a notice. Test: test_trust_anchor › test_a_stricter_flow_or_risk_needs_no_second_word_but_moving_back_does.
3. State template in `references/start.md`: four checklist lines, `Current: Stage 1 – Define`.
4. Docs: spec 12 (`phase`, version 2, names), spec 02 ORC-FR-018.

## Public Surface
- `phase` field in `state.json`; `contract_version` 2
