# KMMIC-Multi-Agents for HF 🫀🤖

**Safety-aware Multi-Agent Clinical Decision Support Prototype for Diuretic Response Assessment**

HF-PathGuard is a clinical AI agent prototype designed for the Korea Clinical Datathon 2026.

The system evaluates early diuretic response and renal/electrolyte safety in ICU patients using multiple specialist agents and an explicit safety-validation layer.

> Current status: **v0.1 prototype**

---

## Target Interface

![HF-PathGuard Dashboard](assets/mock_dashboard_med_agent.png)

> The dashboard above represents the target system design.  
> Some modules including Evidence RAG, patient similarity retrieval, Chief Agent orchestration, and clinician notification are planned for later versions.

---

## Why HF-PathGuard?

Large language models can generate clinically plausible explanations, but they may also:

- misinterpret laboratory values,
- disagree across specialist agents,
- produce low-confidence assessments,
- or generate unsupported recommendations.

HF-PathGuard therefore separates:

**LLM-based clinical reasoning**

from

**deterministic safety validation**

before producing a final clinical review status.

---

## Current Architecture — v0.1

```text
PatientState
     │
     ├─────────────┬─────────────┐
     ↓             ↓             ↓
 Cardiology    Nephrology     Pharmacy
    Agent          Agent          Agent
     └─────────────┼─────────────┘
                   ↓
            Safety Validator
                   ↓
              FinalReport
                   ↓
              OK / REVIEW
