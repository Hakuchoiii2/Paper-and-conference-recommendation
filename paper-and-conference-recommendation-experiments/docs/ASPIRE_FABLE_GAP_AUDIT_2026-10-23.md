# Audit of proposed gaps: ASPIRE, FaBle, and LACE

Date: 2026-10-23. This is a bounded comparison, not a field-wide novelty review. Evidence statements below are separated from proposed research directions. No performance claim is made for the proposed system.

Implementation status is outside this paper audit: a planned module or runnable prototype does not demonstrate a contribution. Mock/synthetic validation can check pipeline behavior but cannot establish real-user intent inference, longitudinal adaptation, conference fit, or retrieval gains.

## Primary-source evidence

**ASPIRE (NAACL 2022).** Its task accepts a query document and an optional subset of query sentences; sentence vectors remain contextualized by the abstract. Aspects may be specified automatically or by users. Its representation is not restricted to a fixed three-label architecture. The three broad categories—background/objective, method, result—describe the CSFCube evaluation. Co-citation text supervises fine-grained matching. Neither its problem formulation nor its reported evaluation establishes a persistent user model or an interactive session-intent inference mechanism. [Sections 2–3, pp. 4454–4457; Section 4, p. 4458](https://aclanthology.org/2022.naacl-main.331.pdf).

**FaBle (ACL 2025).** It synthesizes facet-conditioned training triplets using decomposition, similar/dissimilar fragment generation, and recomposition; triplet learning pulls positives closer and negatives farther away. Scientific-paper experiments name background, method, and result; the method also covers educational facets. A generated summary guides synthesis and is explicitly not guaranteed to be the real facet. Its dissimilar fragments supply negative training examples, not an inference-time request to retrieve a useful alternative method. It does not report a longitudinal user-profile experiment. [Sections 3.1–3.5, pp. 28579–28581; Section 5, pp. 28581–28582](https://aclanthology.org/2025.acl-long.1388.pdf).

**LACE (SIGIR 2023, extended version).** It constructs readable concept profiles from user-interacted documents, learns personalized concept values, supports positive/negative selections and textual edits, and updates recommendations after profile edits. Evaluation includes scientific-paper recommendation, simulations, and an interactive user study. This directly overlaps the broad claims of editable profiles, user control, and feedback-driven recommendation changes. It does not by itself establish the group's exact five-facet schema, session direction inference, or longitudinal update policy. [Sections 1–3 and 5](https://arxiv.org/html/2304.04250v3).

## Claim-by-claim judgment (analysis)

| Proposed contribution | Defensible framing | Weak or unsupported framing |
|---|---|---|
| C1: problem/task/method/dataset/contribution with concept–evidence links | An explicit operational schema and auditable extraction resource, if annotation boundaries, evidence fidelity, and retrieval utility are evaluated. Treat missing evidence as unknown. | “Five facets instead of three is a new retrieval architecture.” Facet count alone does not establish novelty. Do not equate a contribution claim with a result sentence or collapse problem into task without guidelines. |
| C2: infer session focus and desired similar/different direction from query plus feedback, while preserving relevance | Strongest candidate: a measurable intent-learning and constrained ranking problem. Separate which facet matters, desired direction, and contextual relevance. Compare inferred intent with explicit user controls and an oracle. | “Prior work cannot use facets/context” or “FaBle already solves novelty-seeking.” Desiring difference requires useful alternatives, not merely large embedding distance. |
| C3: persistent profile plus search updated over time | A temporal policy that reconciles stable interests with transient session intent, backed by chronological evaluation and ablation of persistence, decay, and session overrides. | “First profile-based/controllable paper recommender.” Generic persistence and editable concepts are insufficient; establish what the update mechanism adds over profile/control prior work. |
| C4: conference facet profiles | A separate venue-fit task with time-indexed venue evidence and held-out future-year evaluation. Assess scope fit and facet compatibility; compare title/topic and paper-centroid baselines. | “New because the two retrieval papers do not recommend venues.” A changed target is not automatically a methodological contribution. Historical acceptance reflects selection biases and does not establish acceptance probability. |

## Recommended central claim and verification

Provisional claim: “We study feedback-based inference of session-specific facet preferences, including similarity versus useful difference, while preserving contextual relevance and separating session intent from persistent interests.” This describes a testable task, not proven field novelty.

Make C1 an enabling representation and evidence-quality contribution; C2 the main research question; C3 a temporal extension only with chronological evidence; C4 a separately evaluated application. Search broader conversational, critiquing, diversity/novelty, temporal recommendation, and venue-recommendation literature before claiming novelty.

Minimum discriminating evaluation: relevance judgments crossed with facet direction; same-query sessions requiring opposite directions; explicit-control and profile-edit baselines; relevance-only and diversity-only rankings; evidence-linked versus unlinked concepts; static versus temporal profiles; temporal splits that prevent future conference papers entering venue profiles. Report relevance and direction satisfaction separately so one cannot hide collapse in the other.

## Claims to remove

- ASPIRE is architecturally limited to exactly three facets.
- FaBle's synthetic dissimilar training fragments prove inference-time novelty control.
- Editable user profiles or profile-based control are new by themselves.
- Absence from these two papers proves a literature-wide gap.
