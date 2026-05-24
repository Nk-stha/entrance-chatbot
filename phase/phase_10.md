# Phase 10 — Prompt Engineering, Guardrails, and Citations

## 1. Goal

Build grounded prompts, enforce context-only answering, validate citations, and refuse unsupported or unsafe answers.

---

## 2. Changes & Deliverables

| Feature/Task | Status | File(s) Affected |
| :--- | :--- | :--- |
| Prompt builder | Done | `backend/generation/prompt_builder.py` |
| Citation extraction/validation | Done | `backend/generation/citation.py` |
| Hallucination guard and confidence scoring | Done | `backend/generation/hallucination.py` |
| Guardrail tests | Done | `backend/tests/test_generation_guardrails.py` |

No known Phase 10 task remains pending in the verified scope.

---

## 3. Technical Implementation Details

- **Key Pattern:** Retrieved chunks are formatted as numbered sources and answer citations must reference valid source numbers.
- **Guardrail:** Missing/invalid citations or no-source answers produce the safe refusal message.
- **Trade-off:** Rule-based citation validation is deterministic and fast, but does not replace a human evaluator for all factual nuance.

---

## 4. Verification (The "Proof")

- **Unit Tests:** `backend/tests/test_generation_guardrails.py` is included in final regression.

```text
79 passed, 3 skipped in 1.86s
```

- **Behavior Evidence:** Cited answers are allowed; missing/invalid citations are refused.

---

## 5. Next Steps

Phase 10 is required for Phase 11 because streaming generation must finalize through guardrails and citations.
