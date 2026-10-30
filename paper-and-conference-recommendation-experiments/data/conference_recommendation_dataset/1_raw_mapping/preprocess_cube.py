"""Offline CSFCube venue mapping. No network, LLM, facet, or other raw source access."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import unicodedata

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
MAPPING = HERE / "venue_mapping.csv"
OUT = HERE / "output"
VERSION = "1.0.1"

# Explicit local allowlist, adapted from the earlier local normalizer, not online results.
# Regex matches identify names, not semantic similarity. Unlisted venues stay unresolved.
SERIES = [
    ("ACL", "Annual Meeting of the Association for Computational Linguistics", ["ACL"], r"(?:annual |\d+(?:st|nd|rd|th) annual )?meeting of (?:the )?association (?:for|of) computational linguistics"),
    ("EMNLP", "Conference on Empirical Methods in Natural Language Processing", ["EMNLP", "HLT/EMNLP"], r"(?:conference on )?empirical methods in natural language processing"),
    ("NAACL", "Conference of the North American Chapter of the Association for Computational Linguistics", ["NAACL", "NAACL-HLT", "HLT-NAACL", "HLT-NAACL, Companion Volume: Short Papers"], r"north american chapter of (?:the )?association (?:for|of) computational linguistics"),
    ("EACL", "Conference of the European Chapter of the Association for Computational Linguistics", ["EACL"], r"european chapter of (?:the )?association (?:for|of) computational linguistics"),
    ("COLING", "International Conference on Computational Linguistics", ["COLING"], r"international conference on computational linguistics(?! and)") ,
    ("IJCNLP", "International Joint Conference on Natural Language Processing", ["IJCNLP"], r"international joint conference on natural language processing"),
    ("CONLL", "Conference on Computational Natural Language Learning", ["CoNLL"], r"conference on (?:computational )?natural language learning"),
    ("LREC", "International Conference on Language Resources and Evaluation", ["LREC"], r"(?:international )?conference on language resources and evaluation"),
    ("RANLP", "International Conference on Recent Advances in Natural Language Processing", ["RANLP"], r"(?:international conference on )?recent advances in natural language processing"),
    ("ICML", "International Conference on Machine Learning", ["ICML"], r"international conference on machine learning(?! (?:and|applications|cybernetics))"),
    ("ICLR", "International Conference on Learning Representations", ["ICLR"], r"international conference on learning representations"),
    ("NEURIPS", "Conference on Neural Information Processing Systems", ["NIPS", "NeurIPS"], r"(?:advances in|conference on) neural information processing systems"),
    ("AAAI", "AAAI Conference on Artificial Intelligence", ["AAAI"], r"(?:aaai|national) conference on artificial intelligence"),
    ("IJCAI", "International Joint Conference on Artificial Intelligence", ["IJCAI"], r"international joint conference on artificial intelligence"),
    ("KDD", "ACM SIGKDD Conference on Knowledge Discovery and Data Mining", ["KDD", "SIGKDD"], r"(?:acm sigkdd )?conference on knowledge discovery (?:and|&) data mining"),
    ("SIGIR", "ACM SIGIR Conference on Research and Development in Information Retrieval", ["SIGIR"], r"(?:acm sigir )?conference on research and development in information retrieval"),
    ("CIKM", "ACM International Conference on Information and Knowledge Management", ["CIKM"], r"conference on information (?:and|&) knowledge management"),
    ("RECSYS", "ACM Conference on Recommender Systems", ["RecSys"], r"(?:acm )?conference on recommender systems"),
    ("CVPR", "IEEE/CVF Conference on Computer Vision and Pattern Recognition", ["CVPR"], r"conference on computer vision and pattern recognition"),
    ("ICCV", "IEEE/CVF International Conference on Computer Vision", ["ICCV"], r"international conference on computer vision"),
    ("ECCV", "European Conference on Computer Vision", ["ECCV"], r"european conference on computer vision"),
    ("ACM_MM", "ACM International Conference on Multimedia", ["ACM MM", "MM", "ACM Multimedia"], r"acm (?:international )?conference on multimedia(?! (?:retrieval|systems))"),
    ("ICASSP", "IEEE International Conference on Acoustics, Speech and Signal Processing", ["ICASSP"], r"international conference on acoustics[,]? speech[,]? and signal processing"),
    ("ICPR", "International Conference on Pattern Recognition", ["ICPR"], r"international conference on pattern recognition(?! applications)"),
    ("CHI", "ACM Conference on Human Factors in Computing Systems", ["CHI"], r"conference on human factors in computing systems"),
    ("WWW", "International World Wide Web Conference", ["WWW"], r"(?:international )?world wide web conference"),
    ("WSDM", "ACM International Conference on Web Search and Data Mining", ["WSDM"], r"conference on web search and data mining"),
    ("SIGMOD", "ACM SIGMOD International Conference on Management of Data", ["SIGMOD", "SIGMOD Conference"], r"(?:international )?conference on management of data"),
    ("SIGDIAL", "SIGDIAL Meeting on Discourse and Dialogue", ["SIGDIAL", "SIGDIAL Conference"], r"sigdial (?:meeting|conference)(?: on discourse and dialogue)?"),
    ("CICLING", "International Conference on Intelligent Text Processing and Computational Linguistics", ["CICLing"], r"(?:international )?conference on intelligent text processing and computational linguistics"),
    ("ICALP", "International Colloquium on Automata, Languages and Programming", ["ICALP"], r"international colloquium on automata, languages[,]? and programming"),
]
JOINT = {
    "ACL_IJCNLP": ("Joint Conference of ACL and IJCNLP", r"\bacl\s*[-/]\s*ijcnlp\b|\bijcnlp\s*[-/]\s*acl\b", {"ACL", "IJCNLP"}),
    "COLING_ACL": ("Joint Conference of COLING and ACL", r"\bcoling\s*[-/]\s*acl\b|\bacl\s*[-/]\s*coling\b|international conference on computational linguistics and (?:\d+(?:st|nd|rd|th) )?(?:annual )?meeting of the association for computational linguistics", {"ACL", "COLING"}),
    "EMNLP_CONLL": ("Joint Conference of EMNLP and CoNLL", r"\bemnlp\s*[-/]\s*conll\b|\bconll\s*[-/]\s*emnlp\b", {"EMNLP", "CONLL"}),
    "ECML_PKDD": ("Joint European Conference on Machine Learning and Principles and Practice of Knowledge Discovery in Databases", r"\becml\s*[-/]\s*pkdd\b|\becml pkdd\b", set()),
}
REGISTRY = {"CONF_" + key: dict(canonical_name=name, acronym=aliases[0], is_joint=False)
            for key, name, aliases, _ in SERIES}
REGISTRY.update({"CONF_" + key: dict(canonical_name=name, acronym=key.replace("_", "-"), is_joint=True)
                 for key, (name, _, _) in JOINT.items()})
JOURNALS = {
    "computational linguistics", "cl", "tacl", "tois", "tods", "talg", "tist", "tslp", "csur", "jacm",
    "taslp", "talip", "tallip", "tcbb", "tchi", "tiis", "tkdd", "togs", "toit", "tweb", "tplp", "toce", "tsec",
    "bioinformatics", "machine learning", "algorithmica", "language", "cognition", "cognitive science", "science", "nature",
    "scientometrics", "plos one", "plos computational biology", "bmc bioinformatics", "information retrieval",
    "knowledge and information systems", "machine translation", "language resources and evaluation", "artificial intelligence",
    "artif. intell.", "artificial intelligence review", "expert syst. appl.", "ieee access", "computer", "neural computation",
    "neural processing letters", "neuroimage", "entropy", "distributed computing", "acta informatica", "theor. comput. sci.",
    "computer speech & language", "computer speech and language", "scientific reports", "speech communication",
    "multimedia systems", "multimedia tools and applications", "social networks", "synthese", "lingua", "theory of computing systems",
    "choice reviews online", "proceedings of the national academy of sciences of the united states of america",
    "proceedings of the ieee", "behavior research methods", "psychological review", "frontiers in psychology",
    "brain and language", "sci. comput. program.", "jasist", "algorithms", "political analysis", "computacion y sistemas",
}
FIELDS = ["venue_raw", "venue_normalized", "raw_record_count", "canonical_paper_count", "mapping_status",
          "venue_type", "conference_id", "rule_id", "review_status", "note"]
INPUTS = {
    "raw": PROJECT / "data/raw/csfcube/abstracts-csfcube-preds.jsonl",
    "source_manifest": PROJECT / "data/raw/csfcube/source_manifest.json",
    "papers": PROJECT / "data/processed/papers.jsonl",
    "id_map": PROJECT / "data/processed/id_map.jsonl",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", html.unescape(value)).casefold()
                    .replace("’", "'").replace("–", "-").replace("—", "-").split())


def decision(status, kind, rule, cid=""):
    return dict(mapping_status=status, venue_type=kind, conference_id=cid, rule_id=rule)


def classify(venue):
    t = normalize(venue)
    if not t:
        return decision("unresolved", "unknown", "missing_venue")
    if re.search(r"instruction file|wspc/|\bpaperijmpc\b", t):
        return decision("unresolved", "unknown", "noisy_venue_text")
    if t in {"arxiv", "arxiv.org", "corr", "ssrn electronic journal"}:
        return decision("unresolved", "preprint", "preprint_only")
    if re.search(r"\bworkshops?\b|\bshared tasks?\b", t):
        return decision("excluded", "workshop", "workshop_marker")
    if re.search(r"\bdemonstrations?\b|\bdemos?\b|\bstudent (?:session|research)\b|\btutorials?\b|\bextended abstracts?\b|\b(?:spring|fall) symposium\b", t):
        return decision("excluded", "auxiliary", "auxiliary_marker")
    # A collocated abbreviation alone doesn't prove workshop vs main/short/demo.
    if "@" in t or ("companion" in t and "short papers" not in t):
        return decision("unresolved", "unknown", "collocated_or_companion_review")
    if t in JOURNALS or re.search(r"\bjournal\b|\btransactions\b|^j\. |\bannals\b", t):
        return decision("excluded", "journal", "journal_name")
    found = set()
    for key, _, aliases, phrase in SERIES:
        acronym = any(re.fullmatch(r"(?:in |proc\.? |proceedings of (?:the )?)?" + re.escape(normalize(a)) +
                                  r"(?:\s*['-]?\s*(?:\d{4}|\d{2}))?(?::? short papers)?[.]?", t) for a in aliases)
        if acronym or re.search(r"\b(?:" + phrase + r")\b", t):
            found.add(key)
    joint = {key for key, (_, pattern, components) in JOINT.items()
             if re.search(pattern, t) or (components and components <= found)}
    if len(joint) == 1:
        key = next(iter(joint))
        # Any extra named series stays ambiguous rather than discarded.
        if found - JOINT[key][2]:
            return decision("unresolved", "unknown", "multiple_series")
        return decision("matched", "conference", "joint_name", "CONF_" + key)
    if joint or len(found) > 1:
        return decision("unresolved", "unknown", "multiple_series")
    if len(found) == 1:
        return decision("matched", "conference", "known_name_or_alias", "CONF_" + next(iter(found)))
    return decision("unresolved", "unknown", "unlisted_venue")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def load_inputs():
    raw_rows = read_jsonl(INPUTS["raw"])
    raw = {str(r["paper_id"]): (n, r) for n, r in enumerate(raw_rows, 1)}
    require(len(raw) == len(raw_rows), "Duplicate CSFCube source ID")
    aliases = [a for a in read_jsonl(INPUTS["id_map"]) if a.get("active") and a["source"] == "csfcube"]
    require(len({a["source_id"] for a in aliases}) == len(aliases), "Duplicate active CSFCube alias")
    require({a["source_id"] for a in aliases} == set(raw), "Raw/active CSFCube alias coverage changed; review first")
    ids = {a["paper_id"] for a in aliases}
    papers = [p for p in read_jsonl(INPUTS["papers"]) if p["paper_id"] in ids]
    require(len(papers) == len(ids) == len({p["paper_id"] for p in papers}), "Missing/duplicate canonical paper")
    require(all(p["source"] == "csfcube" for p in papers), "Unexpected non-CSFCube primary source; review first")
    by_paper = defaultdict(list)
    for a in aliases:
        by_paper[a["paper_id"]].append(a)
    return raw, papers, by_paper


def raw_venue(row):
    value = (row.get("metadata") or {}).get("venue")
    require(value is None or isinstance(value, str), "Invalid raw venue type")
    return value if value is not None else ""


def parse_raw_year(value):
    text = str(value).strip()
    return int(text) if re.fullmatch(r"[0-9]{4}", text) and 1000 <= int(text) <= 2100 else None


def raw_year_fields(evidence):
    candidates = sorted({year for e in evidence if (year := parse_raw_year(e.get("year_raw"))) is not None})
    status = "available" if len(candidates) == 1 else "conflicting" if candidates else "missing"
    return dict(year=candidates[0] if len(candidates) == 1 else None,
                year_source="csfcube_raw.metadata.year", year_status=status, year_candidates=candidates)


def venue_counts(raw, aliases):
    counts = Counter(raw_venue(r) for _, r in raw.values())
    paper_sets = defaultdict(set)
    for pid, aa in aliases.items():
        for a in aa:
            paper_sets[raw_venue(raw[a["source_id"]][1])].add(pid)
    return counts, paper_sets


def initialize_mapping(raw, aliases):
    require(not MAPPING.exists(), "Mapping already exists; edit it explicitly, do not overwrite it")
    counts, paper_sets = venue_counts(raw, aliases)
    with MAPPING.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for venue in sorted(counts, key=lambda v: (-len(paper_sets[v]), normalize(v), v)):
            writer.writerow(dict(venue_raw=venue, venue_normalized=normalize(venue), raw_record_count=counts[venue],
                canonical_paper_count=len(paper_sets[venue]), **classify(venue), review_status="unreviewed",
                note="Quy tắc cục bộ từ tên venue; chưa xác minh từng bài hoặc tra online"))


def load_mapping(raw, aliases):
    with MAPPING.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == FIELDS, "Unexpected mapping columns")
        rows = list(reader)
    mapping = {r["venue_raw"]: r for r in rows}
    counts, paper_sets = venue_counts(raw, aliases)
    require(len(mapping) == len(rows) and set(mapping) == set(counts), "Mapping must cover every exact raw venue once")
    for venue, r in mapping.items():
        require(r["venue_normalized"] == normalize(venue), "Stale normalized venue")
        require(int(r["raw_record_count"]) == counts[venue] and int(r["canonical_paper_count"]) == len(paper_sets[venue]), "Stale venue counts")
        require(r["mapping_status"] in {"matched", "excluded", "unresolved"}, "Invalid mapping status")
        require(r["venue_type"] in {"conference", "journal", "workshop", "auxiliary", "preprint", "unknown"}, "Invalid venue type")
        require(r["review_status"] in {"unreviewed", "rule_reviewed"} and r["note"] and r["rule_id"], "Missing mapping provenance")
        if r["mapping_status"] == "matched":
            require(r["conference_id"] in REGISTRY and r["venue_type"] == "conference", "Invalid matched conference")
            require(bool(venue.strip()), "Cannot map missing venue to a conference")
        else:
            require(not r["conference_id"], "Non-matched venue must not have conference ID")
            if r["mapping_status"] == "excluded":
                require(r["venue_type"] in {"journal", "workshop", "auxiliary"}, "Invalid exclusion")
    return mapping


def combine(evidence):
    useful = [e for e in evidence if e["venue_raw"] and e["venue_raw"].strip() and e["venue_type"] != "preprint"]
    if not useful:
        kind = "preprint" if any(e["venue_type"] == "preprint" for e in evidence) else "unknown"
        return decision("unresolved", kind, "missing_or_preprint_only")
    if any(e["mapping_status"] == "unresolved" for e in useful):
        return decision("unresolved", "unknown", "unresolved_alias_venue")
    labels = {(e["mapping_status"], e["venue_type"], e["conference_id"] or "") for e in useful}
    if len(labels) != 1:
        return decision("unresolved", "unknown", "conflicting_alias_venues")
    status, kind, cid = labels.pop()
    return decision(status, kind, "consistent_raw_aliases", cid)


def make_records(raw, papers, aliases, mapping):
    links = []
    for paper in sorted(papers, key=lambda p: p["paper_id"]):
        evidence = []
        for alias in sorted(aliases[paper["paper_id"]], key=lambda a: a["source_id"]):
            line, native = raw[alias["source_id"]]
            md = native.get("metadata") or {}
            rule = mapping[raw_venue(native)]
            evidence.append(dict(provider="csfcube_raw", source_id=alias["source_id"], raw_line=line,
                raw_path=str(INPUTS["raw"]), venue_raw=md.get("venue"), journal_raw=md.get("journal"),
                year_raw=md.get("year"), identifiers={k: md.get(k) for k in ("doi", "acl_id", "arxiv_id")},
                mapping_status=rule["mapping_status"], venue_type=rule["venue_type"],
                conference_id=rule["conference_id"] or None, rule_id=rule["rule_id"], review_status=rule["review_status"]))
        result = combine(evidence)
        links.append(dict(paper_id=paper["paper_id"], source="csfcube", source_ids=[e["source_id"] for e in evidence],
            conference_id=result["conference_id"] or None, venue_type=result["venue_type"], mapping_status=result["mapping_status"],
            reason=result["rule_id"], verification_level="raw_mapping", publication_year=None, edition_year=None,
            evidence=evidence, **raw_year_fields(evidence)))
    grouped = defaultdict(list)
    for r in links:
        if r["mapping_status"] == "matched":
            grouped[r["conference_id"]].append(r["paper_id"])
    catalog, groups = [], []
    for cid in sorted(grouped):
        observed = sorted({e["venue_raw"] for r in links if r["conference_id"] == cid for e in r["evidence"]
                           if e["conference_id"] == cid})
        catalog.append(dict(conference_id=cid, **REGISTRY[cid], aliases=observed, in_target_catalog=True,
            selection_reason="Tất cả hội nghị nhận diện được từ raw; chưa áp quota hay chọn shortlist thực nghiệm",
            registry_sources=[str(MAPPING)], verification_level="raw_mapping"))
        groups.append(dict(conference_id=cid, paper_ids=grouped[cid], paper_count=len(grouped[cid])))
    validate_records(links, catalog, groups, raw, papers, aliases, mapping)
    return links, catalog, groups


def validate_records(links, catalog, groups, raw, papers, aliases, mapping):
    ids = {p["paper_id"] for p in papers}
    require(len(links) == len(ids) and {r["paper_id"] for r in links} == ids, "Mapping IDs incomplete/duplicated")
    lookup = {r["paper_id"]: r for r in links}
    cids = {r["conference_id"] for r in catalog}
    require(len(cids) == len(catalog) and {g["conference_id"] for g in groups} == cids and len(groups) == len(cids), "Catalog/group mismatch")
    for r in links:
        require(r["source"] == "csfcube" and r["verification_level"] == "raw_mapping", "Unsupported provenance/verification")
        aa = {a["source_id"] for a in aliases[r["paper_id"]]}
        require(len(r["source_ids"]) == len(aa) and set(r["source_ids"]) == aa, "Wrong aliases")
        require(len(r["evidence"]) == len(aa) and {e["source_id"] for e in r["evidence"]} == aa, "Missing evidence")
        require(r["publication_year"] is None and r["edition_year"] is None, "Publication year was inferred")
        require(all(r[k] == v for k, v in raw_year_fields(r["evidence"]).items()), "Raw year/provenance mismatch")
        for e in r["evidence"]:
            line, native = raw[e["source_id"]]
            md = native.get("metadata") or {}
            expected_rule = mapping[raw_venue(native)]
            require(e["provider"] == "csfcube_raw" and e["raw_path"] == str(INPUTS["raw"]) and e["raw_line"] == line,
                    "Wrong evidence source")
            require(all(e[name + "_raw"] == md.get(name) for name in ("venue", "journal", "year")), "Raw metadata changed")
            require(e['identifiers'] == {k: md.get(k) for k in ('doi', 'acl_id', 'arxiv_id')}, "Identifiers changed")
            require(all((e[k] or '') == (expected_rule[k] or '') for k in ('mapping_status', 'venue_type', 'conference_id', 'rule_id', 'review_status')), "Evidence disagrees with mapping CSV")
        d = combine(r["evidence"])
        require((r["mapping_status"], r["venue_type"], r["conference_id"] or '', r["reason"]) ==
                (d["mapping_status"], d["venue_type"], d["conference_id"], d["rule_id"]), "Paper aggregation disagrees")
        if r["mapping_status"] == "matched":
            require(r["conference_id"] in cids and r["venue_type"] == "conference", "Missing conference reference")
        else:
            require(r["conference_id"] is None, "Non-matched paper has a conference ID")
    flat = [pid for g in groups for pid in g["paper_ids"]]
    require(len(flat) == len(set(flat)) and set(flat) == {r["paper_id"] for r in links if r["mapping_status"] == "matched"}, "Group coverage/duplicate error")
    for g in groups:
        require(g["paper_count"] == len(g["paper_ids"]) and all(lookup[pid]["conference_id"] == g["conference_id"] for pid in g["paper_ids"]), "Wrong group count/label")
    for c in catalog:
        require(all(c[k] == REGISTRY[c['conference_id']][k] for k in ('canonical_name', 'acronym', 'is_joint')), "Catalog differs from registry")
        expected_aliases = {e['venue_raw'] for r in links if r['conference_id'] == c['conference_id'] for e in r['evidence'] if e['conference_id'] == c['conference_id']}
        require(set(c['aliases']) == expected_aliases and c['in_target_catalog'] is True, "Catalog alias/selection mismatch")


def self_test():
    cases = [
        ("ACL", "matched", "CONF_ACL"), ("EMNLP 2014", "matched", "CONF_EMNLP"),
        ("SIGIR '02", "matched", "CONF_SIGIR"), ("NIPS", "matched", "CONF_NEURIPS"),
        ("ACL-IJCNLP", "matched", "CONF_ACL_IJCNLP"), ("COLING-ACL", "matched", "CONF_COLING_ACL"),
        ("EMNLP-CoNLL", "matched", "CONF_EMNLP_CONLL"), ("ECML/PKDD", "matched", "CONF_ECML_PKDD"),
        ("HLT-NAACL, Companion Volume: Short Papers", "matched", "CONF_NAACL"),
        ("Proceedings of the AAAI Conference on Artificial Intelligence", "matched", "CONF_AAAI"),
        ("Workshop on Statistical Machine Translation", "excluded", ""),
        ("ACL Workshop on Parsing", "excluded", ""), ("CoNLL Shared Task", "excluded", ""),
        ("ACL: System Demonstrations", "excluded", ""), ("ACL Student Research Workshop", "excluded", ""),
        ("Computational Linguistics", "excluded", ""), ("Machine Learning", "excluded", ""),
        ("Transactions of the Association for Computational Linguistics", "excluded", ""),
        ("Proceedings of the IEEE", "excluded", ""), ("ArXiv", "unresolved", ""),
        ("SSRN Electronic Journal", "unresolved", ""), ("", "unresolved", ""),
        ("ArgMining@ACL", "unresolved", ""), ("WMT", "unresolved", ""),
        ("IWCS", "unresolved", ""),
        ("CHI Companion", "unresolved", ""), ("Unlisted Conference", "unresolved", ""),
        ("International Conference on Machine Learning and Applications", "unresolved", ""),
        ("International Conference on Multimedia Retrieval", "unresolved", ""),
        (" ＡＣＬ ", "matched", "CONF_ACL"),
        ("International Conference on Computational Linguistics and Annual Meeting of the Association for Computational Linguistics", "matched", "CONF_COLING_ACL"),
        ("Proceedings of the 21st International Conference on Computational Linguistics and 44th Annual Meeting of the Association for Computational Linguistics (ACL-06)", "matched", "CONF_COLING_ACL"),
        ("Proceedings of COLING-ACL WSPC/INSTRUCTION FILE paperIJMPC", "unresolved", ""),
    ]
    # The known short-paper companion is an explicit whole-venue alias, not a broad token rule.
    for venue, status, cid in cases:
        got = classify(venue)
        require((got["mapping_status"], got["conference_id"]) == (status, cid), f"Classifier regression: {venue}: {got}")
    def ev(venue):
        return dict(venue_raw=venue, **classify(venue))
    require(combine([ev('ACL'), ev('ArXiv')])['conference_id'] == 'CONF_ACL', 'Preprint alias must not replace conference')
    require(combine([ev('ACL'), ev('EMNLP')])['mapping_status'] == 'unresolved', 'Conflicting conferences must remain unresolved')
    require(combine([ev('ACL'), ev('Computational Linguistics')])['mapping_status'] == 'unresolved', 'Mixed publication types must remain unresolved')
    require(combine([ev('ACL'), ev('Unlisted Conference')])['mapping_status'] == 'unresolved', 'Unknown competing venue must remain unresolved')
    require(combine([ev('ACL'), ev('')])['conference_id'] == 'CONF_ACL', 'Missing alias venue must not erase explicit conference')
    year_cases = [
        (["2014"], 2014, "available", [2014]),
        ([2014, "2014"], 2014, "available", [2014]),
        ([None, ""], None, "missing", []),
        (["unknown", "2014.0", True, 999, 2101], None, "missing", []),
        (["2014", None], 2014, "available", [2014]),
        (["2014", "2015"], None, "conflicting", [2014, 2015]),
        (["2015", "2014"], None, "conflicting", [2014, 2015]),
    ]
    for values, year, status, candidates in year_cases:
        fields = raw_year_fields([dict(year_raw=v) for v in values])
        require((fields["year"], fields["year_status"], fields["year_candidates"]) == (year, status, candidates),
                "Raw years must agree; missing, invalid or conflicting years must not be guessed")
    return len(cases) + 5 + len(year_cases)


def write_jsonl(path, rows):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in rows), encoding='utf-8')


def make_report(links, catalog, groups, raw_count):
    counts = Counter(r['mapping_status'] for r in links)
    types = Counter(r['venue_type'] for r in links)
    names = {c['conference_id']: c['canonical_name'] for c in catalog}
    lines = ['# Kết quả mapping CSFCube từ raw', '',
        '**Chỉ mapping cục bộ từ metadata.venue; không tra DOI/arXiv, không bổ sung nhãn online; pipeline không gọi LLM để gán nhãn.**', '',
        '| Chỉ tiêu | Số lượng |', '|---|---:|', f'| Bản ghi CSFCube raw | {raw_count} |',
        f'| Bài CSFCube sau tiền xử lý chung | {len(links)} |', f'| Matched conference | {counts["matched"]} |',
        f'| Excluded ngoài loại đích | {counts["excluded"]} |', f'| Unresolved chưa rõ | {counts["unresolved"]} |',
        f'| Hội nghị/joint IDs có bài | {len(catalog)} |', '',
        'Matched là nhãn ánh xạ từ raw, **chưa phải đã xác minh nơi công bố hoặc human gold**. '
        'Kiểm tra tự động chỉ xác nhận tính nhất quán; chưa đo precision/recall nhãn.', '',
        '## Phân loại venue', '', '| Loại | Số bài |', '|---|---:|']
    lines += [f'| {k} | {v} |' for k, v in sorted(types.items())]
    lines += ['', '## Hội nghị và danh sách bài', '', '| ID | Tên | Số bài |', '|---|---|---:|']
    lines += [f'| {g["conference_id"]} | {names[g["conference_id"]]} | {g["paper_count"]} |' for g in sorted(groups, key=lambda g: (-g['paper_count'], g['conference_id']))]
    lines += ['', 'Danh sách paper ID nằm trong `conference_papers.jsonl`; lấy title/abstract từ corpus chung bằng ID. '
        'Bảng `../venue_mapping.csv` chứa mọi venue, quy tắc và trạng thái để kiểm tra. '
        'Không có shortlist/quota, split, profile hoặc facet mới trong lần xử lý này.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--init-mapping', action='store_true', help='Create reviewable CSV once; refuses to replace an existing mapping')
    parser.add_argument('--check', action='store_true', help='Validate existing outputs without writing files')
    parser.add_argument('--self-test', action='store_true', help='Run classification/aggregation checks without reading data')
    args = parser.parse_args()
    require(sum((args.init_mapping, args.check, args.self_test)) <= 1, 'Choose one mode')
    ntests = self_test()
    if args.self_test:
        print(json.dumps(dict(self_tests_passed=ntests)))
        return
    input_hashes = {k: sha(p) for k, p in INPUTS.items()}
    raw, papers, aliases = load_inputs()
    if args.init_mapping:
        initialize_mapping(raw, aliases)
        print(json.dumps(dict(mapping_rows=len(venue_counts(raw, aliases)[0]), source='csfcube')))
        return
    mapping = load_mapping(raw, aliases)
    extra_hashes = {'mapping': sha(MAPPING), 'script': sha(Path(__file__))}
    links, catalog, groups = make_records(raw, papers, aliases, mapping)
    report = make_report(links, catalog, groups, len(raw))
    data = {'paper_conference_links.jsonl': links, 'conference_catalog.jsonl': catalog, 'conference_papers.jsonl': groups}
    if args.check:
        manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
        require(manifest['input_hashes'] == input_hashes and manifest['code_and_mapping_hashes'] == extra_hashes, 'Input/code/mapping changed')
        for name, expected in data.items():
            require(read_jsonl(OUT / name) == expected, 'Output differs from deterministic rebuild: ' + name)
        require((OUT / 'report.md').read_text(encoding='utf-8') == report, 'Report differs')
        require(all(sha(OUT / name) == digest for name, digest in manifest['output_hashes'].items()), 'Output hash mismatch')
        require(manifest['counts']['statuses'] == dict(Counter(r['mapping_status'] for r in links)), 'Manifest counts differ')
        print(json.dumps(dict(check='passed', papers=len(links), self_tests_passed=ntests, deterministic_rebuild=True)))
        return
    require(input_hashes == {k: sha(p) for k, p in INPUTS.items()} and extra_hashes['mapping'] == sha(MAPPING), 'Inputs changed during processing')
    OUT.mkdir(exist_ok=True)
    for name, records in data.items():
        write_jsonl(OUT / name, records)
    (OUT / 'report.md').write_text(report, encoding='utf-8')
    manifest = dict(schema_version=VERSION, dataset_version=VERSION, source='csfcube',
        generated_at=datetime.now(timezone.utc).isoformat(), verification_level='raw_mapping',
        network_requests=0, llm_calls=0, human_paper_review_performed=False,
        input_paths={k: str(p) for k, p in INPUTS.items()}, input_hashes=input_hashes,
        code_and_mapping_hashes=extra_hashes,
        counts=dict(raw_records=len(raw), canonical_papers=len(papers), source_aliases=sum(map(len, aliases.values())),
            duplicate_excess=len(raw)-len(papers), venue_mapping_rows=len(mapping), conferences=len(catalog),
            statuses=dict(Counter(r['mapping_status'] for r in links)), venue_types=dict(Counter(r['venue_type'] for r in links)),
            year_statuses=dict(Counter(r['year_status'] for r in links)),
            matched_with_year=sum(r['mapping_status']=='matched' and r['year'] is not None for r in links),
            reasons=dict(Counter(r['reason'] for r in links)),
            mapping_review_statuses=dict(Counter(r['review_status'] for r in mapping.values()))),
        checks=dict(source_and_alias_integrity=True, raw_evidence_preserved=True, grouping_consistent=True,
            inputs_unchanged=True, self_tests_passed=ntests, semantic_label_accuracy='not_measured'),
        output_hashes={name: sha(OUT / name) for name in [*data, 'report.md']})
    (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest['counts'], ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
