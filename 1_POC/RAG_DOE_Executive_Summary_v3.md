# Executive Summary  
## Evaluating Rule-Grounded Responses in a Retrieval-Augmented AI Agent

## 1. Purpose Statement
This experimental series evaluates the optimal design and operation of a Retrieval-Augmented Generation (RAG) agent to reduce hallucinations and other known failure modes.

## 2. Background and Context

AI agents are expected to generate factual and intelligible responses within a defined operational scope. These systems are underpined by large language models. Yet the natue of their training and optimization bias them toward fluent output, which in the absence of relevant information can produce hallucinations —plausible but unsupported responses that conflict with system objectives. Particlularly when applied to technical or instructional tasks.

LLM's are trained on a fixed snapshot of public data.  Accordingly, their repsonses may rely information outside its training set (out of training distribution 'OOD') i.e. not public or out of date (stale). With a bias toward answering the system may hallucinate, overgeneralize from the information avaialve or demonstrate poor refusla behavior by fai
by failing to decline questions they cannot accurately answer.

These limitations can be addressed by **Retrieval-Augmented Generation (RAG)**, a design pattern that provides a language model with access to external up-to-date, and domain-specific information at inference time, allowing responses to be grounded in a verifiable source of truth rather than general knowledge alone.

## 3. Experimental Process and Application Context
For the purposes of experimentation, the AI agent is treated as a **repeatable process** that accepts a question as input and produces a textual response as output. 

The process is evaluated using a fixed, authoritative source document: the official *Clue* rulebook. *Clue* is a deduction game with a compact, unambiguous, and fully specified set of rules, making it suitable as a controlled test domain.

The experimental task is limited to answering factual questions about game rules and mechanics. Strategy, optimization, and off-topic questions are explicitly excluded or required to be refused. This framing allows the agent’s behavior to be evaluated against a clear specification and reduces ambiguity in response evaluation.

---
## 4. Factors and Experimental Design
The experiment uses a **single-factor fixed-effects design**.

- **Factor studied:**  
  Language model temperature. (Termperature controls the variablitliy of the LLM's response. Lower temperature values produce more predictable and repeatable outputs, while higher values increase variation in the generated responses.)

- **Levels:**  
  0.3 (low), 0.5 (medium), 0.8 (high)

- **Experimental unit:**  
  One question answered by the agent at a specified temperature

- **Replication:**  
  A predefined set of questions is used, with each question treated as an independent replicate. Questions are presented in random order, and no conversational history is retained between runs.

- **Blocking by design:**  
  Question types (answerable, misleading, and out-of-scope) are balanced across temperature levels to control for systematic variation due to question category.

All other system parameters, including retrieval configuration and prompt structure, are held constant.

## 5. Response Variable and Measurement
The response variable for the experiment is the **Rule Grounding Score (RGS)**, a composite metric designed to capture both correctness and grounding quality.

Each response is evaluated using the following components:

- **C1 – Correctness (0 or 1):**  
  Correct rule-based answer for answerable questions, or correct refusal for out-of-scope questions.
- **C2 – Rule coverage completeness (0 or 1)**
- **C3 – Citation presence (0 or 1)**
- **C4 – Citation validity (0 or 1)**

The RGS is defined as:

\[
\text{RGS} = C1 \times \frac{(C2 + C3 + C4)}{3}
\]

RGS values range from 0 to 1, where 0 represents an incorrect or hallucinated response and 1 represents a fully correct, properly grounded response or correct refusal.

## 6. Analysis Methodology
The primary analysis uses **one-way Analysis of Variance (ANOVA)** to test for differences in mean RGS across temperature levels.

- **Null hypothesis (H₀):**  
  Mean RGS is equal across all temperature levels.
- **Alternative hypothesis (Hₐ):**  
  At least one temperature level produces a different mean RGS.

Although individual RGS values are bounded, the response variable is continuous on the interval [0,1]. ANOVA assumptions are evaluated using residual diagnostics, including normal probability plots and residuals versus fitted values. If the overall F-test is significant, **Fisher’s Least Significant Difference (LSD)** procedure is used for pairwise comparisons among temperature levels.

## 7. Practical Interpretation
The results of this experiment inform parameter selection for retrieval-augmented AI agents deployed in rule-driven or compliance-sensitive environments. Understanding the relationship between temperature and grounded response quality helps reduce hallucinations and improve refusal behavior, supporting more reliable and auditable AI system operation.

---

## 8. System Design and Implementation Context
The experimental system is implemented using a retrieval-augmented architecture in which the language model has access to a search tool over the authoritative source document. The rulebook is segmented using a semantic chunking strategy based on document structure, with contextual summaries added to preserve meaning during retrieval. A system-level instruction enforces grounding, citation, and refusal requirements. All system design elements are held constant throughout the experiment and are provided for completeness and reproducibility.