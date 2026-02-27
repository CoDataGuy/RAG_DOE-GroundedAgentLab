<p align="center">
  <img src="img/MainBanner.png" width="900">
</p>

# RAG Agent Evaluation Framework  
### Experimental Design, Groundedness Testing, Agent and Workflow Development and Cost-Aware Deployment

This repository documents the evolution of a Retrieval-Augmented Generation (RAG) agent and its associated evaluation framework.  

The expirement(s) use a game teaching agent as surogate for industry applications of RAG where retrieval and answer generation from the grounding documents and not the language model's training is critical.  

The project demonstrates competency in:

- Design of Experiments (RCBD, fractional factorial)
- Statistical analysis (ANOVA, blocking, residual diagnostics)
- Evaluation framework design (composite metrics, gating logic)
- Modular Python architecture
- Prompt configuration management
- Prompt caching & cost optimization
- LLM-as-Judge batch workflows
- Migration toward cost-effective SLM deployment

---

## Project Evolution Roadmap

| Phase | Focus | Competency Demonstrated |
|-------|-------|--------------------------|
| POC Notebook | RAG agent prototype | System understanding |
| RCBD | Temperature study | DOE & statistical design |
| Modularization | Extracted Python modules | Software engineering |
| Prompt Caching | Cost-aware optimization | Systems efficiency |
| LLM-as-Judge | Batch scoring workflow | Scalable evaluation |
| Fractional Factorial | Multi-factor system study | Advanced DOE |
| Multi-Agent | Generalization across domains | Abstraction |
| SLM | Cost-effective deployment | Practical AI engineering |

---

## Key Result (RCBD Example)

Temperature (T=0.3–0.8) had no statistically significant effect on Rule Grounding Score (RGS) under controlled conditions.  
The null result is practically informative: system constraints and retrieval design absorbed sampling variability.

Full report: `\10_RCBD\Results\RCBD clue_rag_report.docx.pdf`

---

## Quickstart

```bash
pip install -r requirements.txt
python run_experiment.py --config configs/rcbd.yaml