# RAG Agent Evaluation Framework  
### Experimental Design, Groundedness Testing, Agent and Workflow Development and Cost-Aware Deployment

This repository documents the evolution of a Retrieval-Augmented Generation (RAG) agent and its associated evaluation framework.  

The expirement(s) use a game teaching agent as surogate for industry applications of RAG where retrieval and answer generation from the grounding documents and not the language model's training is critical.  
 
**Program Goal** is to create an Agnentic System that generates useful answers to procedural questions about different systems (Games) accurately, completely, and fluently.  




#### The project demonstrates competency in:

- Design of Experiments (RCBD, CRD, fractional factorial)
- Prompt Engineering and Optization   
- Statistical analysis (T-test, ANOVA, blocking, residual diagnostics)
- Evaluation framework design (composite metrics, gating logic)
- Modular Python architecture
- Prompt configuration management
- Prompt caching & cost optimization
- LLM-as-Judge batch workflows with Extended Thinking
-  Adversarial test questions
- Scoring validation via MSA (Measurement System Analysis) using Cohen's Kappa 
- Migration toward cost-effective SLM deployment

---

#### Project Evolution Roadmap
Each step resulted in discoveries of new defects 

| Phase | Focus | Competency Demonstrated |
|-------|-------|--------------------------|
| POC Notebook | RAG agent prototype | System understanding |
| RCBD | Temperature study | DOE & statistical design |
| Modularization | Extracted Python modules | Software engineering |
| Prompt Caching | Cost-aware optimization | Systems efficiency |
| LLM-as-Judge | Batch scoring workflow | Scalable evaluation |
| Advanced Evaluation| Extended Thinking, Adversarial Questions| MSA|
| Fractional Factorial | Multi-factor system study | Advanced DOE |
| Multi-Agent | Generalization across domains | Abstraction |
| SLM | Cost-effective deployment | Practical AI engineering |

---

### Key Result (RCBD Example)

Temperature (T=0.3–0.8) had no statistically significant effect on Rule Grounding Score (RGS) under controlled conditions.  
The null result is practically informative: system constraints and retrieval design absorbed sampling variability.

Full report: `docs/02_experiments_rcbd.md`
