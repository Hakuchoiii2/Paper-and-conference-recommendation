# Dataset D: scientific search sessions and interaction logs

Checked 2026-10-23. Primary sources only. Access statements below distinguish a published release from a successfully retrieved data file. No complete archive was downloaded during this check.

## Best candidate: Sowiport User Search Sessions (SUSS)

- Official catalogue: [GESIS SUSS, DOI 10.7802/1380](https://search.gesis.org/research_data/SDN-10.7802-1380?doi=10.7802%2F1380). It explicitly states **free access without registration** and **CC BY-NC-ND 4.0**. This is the dataset license; the paper's arXiv license is separate.
- [Authors' dataset paper](https://arxiv.org/html/1706.00816v3), Section 3: scientific-library searches, collected 2014-04-02 through 2015-04-02; 58 action types. Documented information includes cookie-assigned session identifier, timestamp, query terms, document IDs, result lists, action order and duration. Examples include `query_form`, `search`, `view_record`, `view_description`, and `to_favorites`. A 20-minute inactivity boundary defines a search session. The paper reports 484,449 filtered sessions and 7,982,427 log entries.
- Identifier limit: a cookie identifies browser activity, not a verified researcher identity. Session histories can support session-based experiments; do not claim a clean longitudinal researcher profile without checking the released identifiers and schema.
- Access caveat: the official record is indexed and the release is documented, but DOI resolution failed in this browsing environment and the catalogue rendered only its shell when opened. A direct original archive was not retrieved. Treat ingestion as pending, not completed.
- Content caveat: `view_description` records an abstract-view action; it does not establish that abstract text is distributed. A document-ID-to-title/abstract mapping and metadata coverage remain unverified. Do not promise semantic candidate ranking from these logs alone.

## Useful follow-up: SUSS-16-17

[Official GESIS AMUR GitLab repository](https://git.gesis.org/amur/SUSS-16-17) lists a later September 2016–May 2017 release: 208,556 searches and 3,376,997 log entries. It includes `suss_16_17.zip` (Git LFS; containing CSV), SQL table creation/loading scripts, `table_description.csv`, and action mappings. This provides a more concrete ingestion lead than a paper alone. Raw schema URLs were inaccessible to this browser tool, so exact CSV column names were **not verified**. The README excerpt did not establish a separate license; do not automatically copy the original SUSS license to this follow-up. The [official GESIS project catalogue](https://www.gesis.org/forschung/forschungsbereich-computational-methods-alt/gesis-labs/kts-research-labs) also links both releases. That page reports a different original session count (558,008); preserve the release/filter version rather than mixing counts.

Additional direct access check: HEAD requests to the GitLab raw ZIP and project-1035 schema API failed DNS resolution in the local environment. There is therefore no verified downloadable ZIP payload or verified absence of a login requirement from this check. The release listing itself is publicly indexed.

## RARD / RARD II: usable click evidence, different experimental unit

[RARD authors' paper](https://www.dlib.org/dlib/july17/beel/07beel.html) documents recommendation-set ID, source-document ID, recommended-document ID, rank, delivery/request timestamps, click timestamp or NULL, and algorithm parameters. License: CC BY 3.0. Document metadata is excluded for copyright reasons; external IDs are provided. The documented release endpoint is [data.mr-dlib.org](http://data.mr-dlib.org), identified as Harvard Dataverse, but this check could not reach it.

[RARD II authors' paper](https://researchrepository.ucd.ie/rest/bitstreams/42554/retrieve), Sections 3.1–3.2, describes 94 million recommendations and matrices with source/recommended paper IDs, display counts, click counts and CTR. Its matrix notation `src_doc_id (user)` is a **source article**, not a person. A recommendation request/set is not an authentic user search session. The paper also warns that non-clicks may reflect unseen recommendations or bots. Use RARD for source-paper → candidate-paper click/CTR evaluation, conditional on acquiring the archive. Do not use it to claim user-history personalization, query reformulation, or true similar/different labels.

## PubCLogs: scientific evidence, no verified public release

[Shin et al., Harnessing PubMed User Query Logs for Post Hoc Explanations of Recommended Similar Articles](https://pmc.ncbi.nlm.nih.gov/articles/PMC11188129/) constructs PubCLogs from 2020–2023 PubMed co-clicks. It aggregates article pairs with associated queries/click counts, then derives title-token explanation targets. After filtering, the paper reports approximately 1.5M train, 47k development and 47k test pairs. The public paper inspected here contains no dataset download, repository link, or dataset license. Search did not establish a public archive. Thus **do not list PubCLogs as downloadable** or assume raw sessions/user IDs are released. Its task is explanation token selection, not supervised semantic similar/different classification.

## Additional public PubMed log lead, with severe feature loss

[NLM's PubMed User Behavior Study download page](https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/LogStudy/) lists transformed logs with scrambled session ID, seconds-from-midnight, query/abstract/fulltext action, query-token count, returned-citation count and clicked rank. It links a 10,000-line [sample](https://www.ncbi.nlm.nih.gov/CBBresearch/Lu/LogStudy/sample.txt) and a full archive. The sample endpoint resolved, but the full archive did not. No dataset license was established on this page. Crucially, the advertised fields contain neither query text nor PMID/document identity: this cannot directly train a query-to-paper ranker or reconstruct clicked-paper semantics.

## Experimental recommendation (inference)

Prioritize SUSS for D, subject to retrieving and inspecting the real archive. Preserve anonymized identifier meaning, time ordering, and session boundaries. Treat next document view/click as implicit behavior; do not invent human-annotated similarity/dissimilarity labels. Keep RARD as a separate item-to-item implicit-feedback benchmark. Keep PubCLogs as related work until an actual licensed release is found. No source above provides conference-recommendation ground truth.
