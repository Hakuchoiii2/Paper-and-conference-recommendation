# A handoff, gold review selection and B–E datasets

Approved in chat on 2026-10-05: implement dataset generators with README target
counts, merge five A parts and choose the 400 most complete annotations for
human gold review. Preserve existing uncommitted A changes.

## Shared requirements

Python 3.11+, standard library only; reuse corpus I/O, normalization and validators.
Canonical corpus: `data/processed/papers.jsonl`; preserve IDs and text. B–E require
validated complete A silver and metadata. Do not fabricate facets or silently use
partial inputs. Skip unavailable samples and report actual counts and shortfalls.
Queries, labels and behavior remain mock. Separate observable data and truth.
Record seed 42, input/config/generator hashes and deterministic output checksums.

## A merge and 400-review queue

Validate each part using A's existing checker. Require common corpus, prompt,
guideline, model and extraction provenance; reject overlaps or missing coverage
before publishing the complete handoff. Compare available runtime model identities
and resolved revisions, allowing fallback records without those fields. Export sorted silver/metadata and a
manifest recording source-part hashes, fallback audit and facet coverage.

Gold selection is deterministic: exclude prompt-development P000001, fallback or
quality-error annotations and records with no facets. Sort descending by number
of nonempty facets, then number of supported concepts, then ascending paper ID.
Select 400 with rank and completeness recorded. Fewer than 400 eligible papers
is an error, never a fabricated quota. Paper text and pending human annotation
forms are separate from silver references. Do not create `facets_gold.jsonl` or
overwrite an existing review queue. This deliberately selected subset favors
complete silver; evaluation must report that selection bias.

## B and C

B: 300 queries × 100 candidates, balanced over five facets when feasible.
Use the corpus normalizer without semantic aliases. Nonempty equal concept sets
score 2, intersecting unequal sets score 1, disjoint sets score 0; missing target
facets are ineligible. Include positives and negatives, prefer hard negatives
sharing another facet. Group train/dev/test by anchor.

C: 1,500 cases; six templates × 200 and two × 150. Each template defines all five
directions. Similar = overlap; different = nonempty disjoint; ignore = no rule.
All active constraints must hold. Default 20 candidates/case (README has no C
candidate quota), with positives and negatives. Prefer negatives violating only
one rule. One case per anchor/template; skip shortages and report gaps by type.

## D and E

D: 300 users × 50 events, 30 history + 20 future. Generate profiles before events,
finite weights in [-1,1]. Mix uniform exposure with exposure to papers matching
profile concepts; configure the mixing rate, noise and behavior thresholds.
Affinity = mean weight across paper concepts, unseen concepts contributing zero.
Noisy affinity maps to five interaction types. Strictly ordered UTC timestamps.
Unobserved papers are not negative labels.

E: same D user IDs, independent events and initial profiles. Four consecutive
monthly periods, three history and one holdout. Default 15 events/user/period =
18,000 events, 1,200 profiles, within the README 15,000–20,000 target. Half stable,
half interpolate old→transition→new→new with coefficients [0,0.5,1,1]. Groups,
weights and future data belong only in evaluation truth.
Observable D/E behavior distributions count history events only, never holdout outcomes.

## Acceptance

Exercise corrupted references, labels, missing facets, hidden truth, hashes and
time boundaries. Check byte-identical rebuilds and target-sized outputs on
explicitly test-only fixtures. Real B–E runs require all 4,210 A annotations.
