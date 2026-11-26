"""Self-contained CSFCube mapping + identifier metadata pipeline; offline by default."""
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
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
MAPPING = HERE / "venue_mapping.csv"
OUT = HERE / "output"
VERSION = "2.0.1"
CACHE = HERE / "cache"
CACHE_DATA = CACHE / "metadata.jsonl"
CACHE_MANIFEST = CACHE / "manifest.json"

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


EXTRA_SERIES = [
    ('INTERSPEECH', 'Interspeech', ['Interspeech'], r'\binterspeech\b'),
    ('ICDM', 'IEEE International Conference on Data Mining', ['ICDM'], r'ieee (?:international )?conference on data mining'),
    ('ICME', 'IEEE International Conference on Multimedia and Expo', ['ICME'], r'conference on multimedia and expo'),
    ('ICRA', 'IEEE International Conference on Robotics and Automation', ['ICRA'], r'conference on robotics and automation'),
    ('IROS', 'IEEE/RSJ International Conference on Intelligent Robots and Systems', ['IROS'], r'conference on intelligent robots and systems'),
    ('ICWSM', 'International AAAI Conference on Web and Social Media', ['ICWSM'], r'conference on web and social media'),
    ('AIIDE', 'AAAI Conference on Artificial Intelligence and Interactive Digital Entertainment', ['AIIDE'], r'artificial intelligence and interactive digital entertainment'),
    ('ICMLA', 'International Conference on Machine Learning and Applications', ['ICMLA'], r'conference on machine learning and applications'),
    ('ICMLC', 'International Conference on Machine Learning and Cybernetics', ['ICMLC'], r'conference on machine learning and cybernetics'),
    ('ICSC', 'IEEE International Conference on Semantic Computing', ['ICSC'], r'conference on semantic computing'),
    ('ICFHR', 'International Conference on Frontiers in Handwriting Recognition', ['ICFHR'], r'conference on frontiers in handwriting recognition'),
    ('WACV', 'IEEE Winter Conference on Applications of Computer Vision', ['WACV'], r'conference on applications of computer vision'),
    ('IJCNN', 'International Joint Conference on Neural Networks', ['IJCNN'], r'international joint conference on neural networks'),
    ('CIG', 'IEEE Conference on Computational Intelligence and Games', ['CIG'], r'conference on computational intelligence and games'),
    ('SMC', 'IEEE International Conference on Systems, Man and Cybernetics', ['SMC'], r'conference on systems[,]? man[,]? and cybernetics'),
    ('COMPSAC', 'International Computer Software and Applications Conference', ['COMPSAC'], r'computer software and applications conference'),
    ('ASONAM', 'International Conference on Advances in Social Networks Analysis and Mining', ['ASONAM'], r'conference on advances in social networks analysis and mining'),
    ('BIGDATA', 'IEEE International Conference on Big Data', [], r'ieee.*conference on big data'),
    ('ECIR', 'European Conference on Information Retrieval', ['ECIR'], r'european conference on information retrieval'),
    ('TSD', 'International Conference on Text, Speech and Dialogue', ['TSD'], r'conference on text[,]? speech[,]? and dialogue'),
    ('AISTATS', 'International Conference on Artificial Intelligence and Statistics', ['AISTATS'], r'conference on artificial intelligence and statistics'),
    ('CSCW', 'ACM Conference on Computer-Supported Cooperative Work', ['CSCW'], r'conference on computer[- ]supported cooperative work'),
    ('UIST', 'ACM Symposium on User Interface Software and Technology', ['UIST'], r'symposium on user interface software and technology'),
    ('SODA', 'ACM-SIAM Symposium on Discrete Algorithms', ['SODA'], r'symposium on discrete algorithms'),
    ('GECCO', 'Genetic and Evolutionary Computation Conference', ['GECCO'], r'conference on genetic and evolutionary computation|genetic and evolutionary computation conference'),
    ('HT', 'ACM Conference on Hypertext and Social Media', [], r'conference on hypertext(?: and social media)?'),
    ('WEBSCI', 'ACM Web Science Conference', ['WebSci'], r'web science conference'),
    ('PACLIC', 'Pacific Asia Conference on Language, Information and Computation', ['PACLIC'], r'pacific asia conference on language[,]? information and computation'),
    ('AMTA', 'Conference of the Association for Machine Translation in the Americas', ['AMTA'], r'conference (?:of the association for|on) machine translation in the americas'),
    ('MICCAI', 'International Conference on Medical Image Computing and Computer-Assisted Intervention', ['MICCAI'], r'conference on medical image computing and computer[- ]assisted intervention'),
    ('ECML', 'European Conference on Machine Learning', ['ECML'], r'european conference on machine learning'),
    ('WMT', 'Conference on Machine Translation', [], r'\bconference on machine translation\b'),
    ('ICDAR', 'International Conference on Document Analysis and Recognition', ['ICDAR'], r'conference on document analysis and recognition'),
    ('ICSE', 'International Conference on Software Engineering', ['ICSE'], r'conference on software engineering'),
    ('ICDE', 'IEEE International Conference on Data Engineering', ['ICDE'], r'conference on data engineering'),
    ('ICIP', 'IEEE International Conference on Image Processing', ['ICIP'], r'conference on image processing'),
    ('ICTAI', 'IEEE International Conference on Tools with Artificial Intelligence', ['ICTAI'], r'conference on tools with artificial intelligence'),
    ('FOCS', 'IEEE Symposium on Foundations of Computer Science', ['FOCS'], r'symposium on foundations of computer science'),
    ('STOC', 'ACM Symposium on Theory of Computing', ['STOC'], r'symposium on theory of computing'),
    ('SAC', 'ACM Symposium on Applied Computing', ['SAC'], r'symposium on applied computing'),
    ('SDM', 'SIAM International Conference on Data Mining', ['SDM'], r'siam.*conference on data mining'),
    ('ESWC', 'Extended Semantic Web Conference', ['ESWC'], r'extended semantic web conference'),
    ('WI', 'IEEE/WIC/ACM International Conference on Web Intelligence', [], r'conference on web intelligence'),
    ('CCS', 'ACM Conference on Computer and Communications Security', [], r'conference on computer and communications security'),
    ('ECOOP', 'European Conference on Object-Oriented Programming', ['ECOOP'], r'european conference on object[- ]oriented programming'),
    ('CICLING', 'International Conference on Intelligent Text Processing and Computational Linguistics', [], r'conference on computational linguistics and intelligent text processing'),
    ('WWW', 'International World Wide Web Conference', ['The Web Conference'], r'conference on world wide web'),
    ('NEURIPS', 'Conference on Neural Information Processing Systems', ['Neural Information Processing Systems'], r'^neural information processing systems$'),
    ('CVPR', 'IEEE/CVF Conference on Computer Vision and Pattern Recognition', ['Computer Vision and Pattern Recognition'], r'^computer vision and pattern recognition$'),
]
for _key, _name, _aliases, _phrase in EXTRA_SERIES:
    REGISTRY.setdefault('CONF_' + _key, dict(canonical_name=_name, acronym=_aliases[0] if _aliases else _key, is_joint=False))
REGISTRY['CONF_NLPCC_ICCPOL'] = dict(canonical_name='Joint NLPCC-ICCPOL Conference', acronym='NLPCC-ICCPOL', is_joint=True)
BASE_FIELDS = FIELDS[:]
FIELDS = BASE_FIELDS + ['origin', 'metadata_record_count']


def classify_expanded(venue):
    old = classify(venue)
    if old['mapping_status'] == 'excluded' or old['venue_type'] == 'preprint' or old['rule_id'] in {
        'missing_venue', 'noisy_venue_text', 'collocated_or_companion_review', 'multiple_series'}:
        return old
    t = normalize(venue)
    if re.search(r'\bnlpcc\s*[-/]\s*iccpol\b', t):
        return decision('matched', 'conference', 'expanded_joint_name', 'CONF_NLPCC_ICCPOL')
    if re.search(r'\becml\s*[-/ ]\s*pkdd\b|machine learning and knowledge discovery in databases', t):
        return decision('matched', 'conference', 'expanded_joint_name', 'CONF_ECML_PKDD')
    found = {old['conference_id']} if old['conference_id'] else set()
    for key, _, aliases, phrase in EXTRA_SERIES:
        exact = any(re.fullmatch(r'(?:in |proc\.? |proceedings of (?:the )?)?' + re.escape(normalize(a)) +
                                r"(?:\s*['-]?\s*(?:\d{4}|\d{2}))?[.]?", t) for a in aliases)
        if exact or re.search(r'\b(?:' + phrase + r')\b', t):
            found.add('CONF_' + key)
    if 'CONF_AIIDE' in found:
        found.discard('CONF_AAAI')
    if 'CONF_SDM' in found:
        found.discard('CONF_ICDM')
    if len(found) == 1:
        cid = next(iter(found))
        return old if cid == old['conference_id'] else decision('matched', 'conference', 'expanded_name_or_alias', cid)
    if found:
        return decision('unresolved', 'unknown', 'multiple_series')
    return old


def title_key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', html.unescape(value or '')).casefold() if c.isalnum())


def doi_key(value):
    value = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', str(value or '').strip(), flags=re.I).casefold()
    return value if re.fullmatch(r'10\.\d{4,9}/\S+', value) else ''


def json_digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def cache_record(provider, lookup, item, response, origin):
    body = dict(provider=provider, lookup=lookup, item=item)
    return dict(body, record_id=json_digest(body), request_url=response['url'],
                retrieved_at=response['retrieved_at'], origin=origin)


def load_cache():
    require(CACHE_DATA.is_file() and CACHE_MANIFEST.is_file(), 'Local cache missing: initialize with --import-cache or --fetch-missing')
    manifest = json.loads(CACHE_MANIFEST.read_text(encoding='utf-8'))
    require(sha(CACHE_DATA) == manifest['metadata_sha256'], 'Local metadata cache hash mismatch')
    records = read_jsonl(CACHE_DATA)
    require(len(records) == manifest['records'] and len({r['record_id'] for r in records}) == len(records), 'Cache count/duplicate error')
    for r in records:
        require(r['provider'] in {'crossref', 'semantic_scholar'}, 'Unsupported cache provider')
        require(r['record_id'] == json_digest({k: r[k] for k in ('provider', 'lookup', 'item')}), 'Cache item changed')
        require('query.title=' not in r['request_url'] and r['retrieved_at'], 'Unanchored title lookup in cache')
        host = urllib.parse.urlsplit(r['request_url']).hostname
        require(host == ('api.crossref.org' if r['provider'] == 'crossref' else 'api.semanticscholar.org'), 'Wrong API provenance')
        if r['provider'] == 'crossref':
            require(r['lookup']['kind'] == 'doi' and bool(doi_key(r['item'].get('DOI'))) and
                    r['lookup']['value'] == doi_key(r['item'].get('DOI')), 'Cached DOI/lookup mismatch')
        else:
            require(r['lookup']['kind'] == 's2_corpus_id' and
                    r['lookup']['value'] == str((r['item'].get('externalIds') or {}).get('CorpusId')), 'Cached CorpusId/lookup mismatch')
    return records, manifest


def save_cache(records, provenance, **extra):
    CACHE.mkdir(exist_ok=True)
    unique = {r['record_id']: r for r in records}
    rows = [unique[k] for k in sorted(unique)]
    write_jsonl(CACHE_DATA, rows)
    manifest = dict(cache_version='1.0.0', content='Identifier API records, not previous paper labels',
        records=len(rows), providers=dict(Counter(r['provider'] for r in rows)),
        metadata_sha256=sha(CACHE_DATA), imported_sources=provenance, **extra)
    CACHE_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def desired_dois(raw, records):
    dois = {doi_key((r.get('metadata') or {}).get('doi')) for _, r in raw.values()}
    for r in records:
        if r['provider'] != 'semantic_scholar' or r['lookup']['value'] not in raw:
            continue
        native = raw[r['lookup']['value']][1]
        if title_key(native['title']) == title_key(r['item'].get('title')) and len(title_key(native['title'])) >= 20:
            dois.add(doi_key((r['item'].get('externalIds') or {}).get('DOI')))
    return dois - {''}


def import_identifier_cache(source_root, raw):
    # The only legacy inputs permitted are original API response files in these two directories.
    source_root = Path(source_root).resolve()
    dirs = [source_root / 'conference_verification_round2/evidence_cache', source_root / 'conference_verification_round3/evidence_cache']
    require(all(d.is_dir() for d in dirs), 'Expected Extra_DOING root with both evidence_cache directories')
    records, crossref_responses, origins = [], [], []
    stats = Counter()
    for folder in dirs:
        for path in sorted(folder.glob('*.json')):
            if not path.name.startswith(('s2_', 'crossref_')):
                continue
            response = json.loads(path.read_text(encoding='utf-8'))
            if not response.get('ok') or 'query.title=' in response.get('url', ''):
                stats['failed_or_title_search_responses_skipped'] += 1
                continue
            origin = dict(path=str(path), sha256=sha(path))
            source = response.get('source')
            if source == 's2':
                requested = (response.get('payload') or {}).get('ids') or []
                payload = response.get('data') or []
                require(len(requested) == len(payload), 'Semantic Scholar cache response length mismatch')
                for query, item in zip(requested, payload):
                    sid = query.removeprefix('CorpusId:')
                    if not item or not query.startswith('CorpusId:') or sid not in raw:
                        continue
                    if str((item.get('externalIds') or {}).get('CorpusId')) != sid:
                        stats['corpus_id_mismatches_skipped'] += 1
                        continue
                    records.append(cache_record('semantic_scholar', dict(kind='s2_corpus_id', value=sid), item, response, origin))
                origins.append(origin)
            elif source in {'crossref', 'crossref_authors'}:
                crossref_responses.append((response, origin))
    allowed = desired_dois(raw, records)
    for response, origin in crossref_responses:
        if urllib.parse.urlsplit(response['url']).hostname != 'api.crossref.org':
            continue
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(response['url']).query)
        if not any('doi:' in f for f in query.get('filter', [])):
            continue
        used = False
        for item in (response.get('data') or {}).get('message', {}).get('items', []):
            doi = doi_key(item.get('DOI'))
            if doi and doi in allowed:
                records.append(cache_record('crossref', dict(kind='doi', value=doi), item, response, origin))
                used = True
        if used:
            origins.append(origin)
    require(any(r['provider'] == 'crossref' for r in records), 'No usable identifier Crossref responses imported')
    save_cache(records, sorted({o['path']: o for o in origins}.values(), key=lambda o: o['path']),
        bootstrap=dict(source=str(source_root), network_requests=0, skipped=dict(stats)))


def fetch_missing(raw, records, cache_manifest, limit):
    # Optional explicit refresh: exact identifiers only; no title, arXiv, or free-form search.
    have = {r['lookup']['value'] for r in records if r['provider'] == 'crossref'}
    pending = sorted(desired_dois(raw, records) - have)
    selected = pending if limit == 0 else pending[:limit]
    errors = []
    for doi in selected:
        url = 'https://api.crossref.org/works/' + urllib.parse.quote(doi, safe='')
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'CSFCubeVenueMetadata/2.0 (identifier-only research preprocessing)'})
            with urllib.request.urlopen(req, timeout=30) as response:
                item = json.load(response)['message']
            require(doi_key(item.get('DOI')) == doi, 'Returned DOI differs from request')
            response_info = dict(url=url, retrieved_at=datetime.now(timezone.utc).isoformat())
            records.append(cache_record('crossref', dict(kind='doi', value=doi), item, response_info,
                                        dict(path='fetched_by_this_script', sha256=json_digest(item))))
        except (urllib.error.URLError, ValueError, KeyError) as error:
            errors.append(dict(doi=doi, error=str(error)))
        time.sleep(1)
    save_cache(records, cache_manifest.get('imported_sources', []),
               refresh=dict(requests=len(selected), errors=errors, pending_before=len(pending)))
    return len(selected)


def best_crossref(records):
    grouped = defaultdict(list)
    for r in records:
        if r['provider'] == 'crossref':
            grouped[r['lookup']['value']].append(r)
    # Prefer the snapshot containing authors; then latest retrieval, then stable content ID.
    return {doi: max(rr, key=lambda r: (bool(r['item'].get('author')), r['retrieved_at'], r['record_id']))
            for doi, rr in grouped.items()}


def metadata_venue(item):
    return '; '.join(item.get('container-title') or [])


def expanded_mapping(raw, aliases, records, prepare=False):
    counts, sets = venue_counts(raw, aliases)
    meta_counts = Counter(metadata_venue(r['item']) for r in best_crossref(records).values())
    keys = set(counts) | set(meta_counts)
    with MAPPING.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames
        previous = list(reader)
    initial = columns == BASE_FIELDS
    require(columns in (BASE_FIELDS, FIELDS), 'Unexpected expanded mapping schema')
    old = {r['venue_raw']: r for r in previous}
    require(len(old) == len(previous), 'Duplicate mapping venue')
    if prepare:
        rows = []
        for venue in sorted(keys, key=lambda v: (-len(sets[v]), normalize(v), v)):
            generated = dict(classify_expanded(venue), review_status='unreviewed',
                             note='Quy tắc tên cục bộ; không phải human gold')
            if venue in old and not initial:
                generated = {k: old[venue][k] for k in ('mapping_status', 'venue_type', 'conference_id', 'rule_id', 'review_status', 'note')}
            rows.append(dict(venue_raw=venue, venue_normalized=normalize(venue), raw_record_count=counts[venue],
                canonical_paper_count=len(sets[venue]), **generated,
                origin='raw+metadata' if venue in counts and venue in meta_counts else 'raw' if venue in counts else 'metadata',
                metadata_record_count=meta_counts[venue]))
        with MAPPING.open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        old = {r['venue_raw']: r for r in rows}
    require(not initial or prepare, 'Prepare stage-2 mapping first with --prepare-mapping')
    require(set(old) == keys, 'Mapping/cache inventory changed: run --prepare-mapping to add/update rows')
    for venue, r in old.items():
        require(r['venue_normalized'] == normalize(venue), 'Normalized name mismatch')
        require(int(r['raw_record_count']) == counts[venue] and int(r['canonical_paper_count']) == len(sets[venue]) and
                int(r['metadata_record_count']) == meta_counts[venue], 'Mapping counts changed: run --prepare-mapping')
        require(r['mapping_status'] in {'matched', 'excluded', 'unresolved'} and r['rule_id'] and r['note'], 'Invalid mapping decision')
        require(r['review_status'] in {'unreviewed', 'rule_reviewed'}, 'Invalid rule review level')
        if r['mapping_status'] == 'matched':
            require(bool(venue.strip()) and r['conference_id'] in REGISTRY and r['venue_type'] == 'conference', 'Invalid matched ID')
        else:
            require(not r['conference_id'], 'Non-matched row has conference ID')
            if r['mapping_status'] == 'excluded':
                require(r['venue_type'] in {'journal', 'workshop', 'auxiliary'}, 'Invalid exclusion type')
    return old


def authors_check(local_authors, remote_authors):
    local = [(title_key(a.get('last')), title_key(a.get('first'))) for a in local_authors if a.get('last')]
    remote = [(title_key(a.get('family')), title_key(a.get('given'))) for a in remote_authors if a.get('family')]
    if not local or not remote:
        return 'unavailable'
    overlap = {a[0] for a in local} & {a[0] for a in remote}
    first_agrees = local[0][0] == remote[0][0] and bool(local[0][1] and remote[0][1]) and local[0][1][0] == remote[0][1][0]
    return 'matched' if len(overlap) >= 2 or first_agrees else 'mismatched'


def select_metadata(row, paper, raw, records_by_sid, crossref, mapping):
    direct = {doi_key((raw[sid][1].get('metadata') or {}).get('doi')) for sid in row['source_ids']} - {''}
    bindings = {doi: dict(kind='raw_doi', source_ids=[sid for sid in row['source_ids']
                if doi_key((raw[sid][1].get('metadata') or {}).get('doi')) == doi]) for doi in sorted(direct)}
    for sid in row['source_ids']:
        for r in records_by_sid.get(sid, []):
            item = r['item']
            if title_key(paper['title']) != title_key(item.get('title')) or len(title_key(paper['title'])) < 20:
                continue
            doi = doi_key((item.get('externalIds') or {}).get('DOI'))
            if doi and doi not in bindings:
                bindings[doi] = dict(kind='corpus_id_to_doi', source_ids=[sid], connector_record_id=r['record_id'])
    result = []
    for doi, binding in sorted(bindings.items()):
        if doi not in crossref:
            continue
        r = crossref[doi]
        item = r['item']
        remote_title = ' '.join(item.get('title') or [])
        local_authors = (raw[binding['source_ids'][0]][1].get('metadata') or {}).get('authors') or []
        author_status = authors_check(local_authors, item.get('author') or [])
        title_matches = bool(title_key(paper['title'])) and title_key(paper['title']) == title_key(remote_title)
        accepted = title_matches and author_status != 'mismatched' and (
            binding['kind'] == 'raw_doi' or author_status == 'matched')
        if len(title_key(paper['title'])) < 20 and author_status != 'matched':
            accepted = False
        venue = metadata_venue(item)
        d = {k: mapping[venue][k] for k in ('mapping_status', 'venue_type', 'conference_id', 'rule_id')}
        # A conference serial may register journal-article; other such conflicts need review.
        if d['mapping_status'] == 'matched' and item.get('type') == 'journal-article' and not re.search(
            r'proceedings of the (?:international )?aaai conference', normalize(venue)):
            d = decision('unresolved', 'unknown', 'crossref_type_conflict')
        dates = (item.get('published') or {}).get('date-parts') or [[]]
        year = dates[0][0] if dates and dates[0] and isinstance(dates[0][0], int) and 1000 <= dates[0][0] <= 2100 else None
        result.append(dict(provider='crossref', cache_record_id=r['record_id'], identifier_binding=binding,
            doi=doi, record_title=remote_title, venue_raw=venue, publication_type=item.get('type'),
            publication_year=year, title_check='matched' if title_matches else 'mismatched', author_check=author_status,
            identity_accepted=accepted, url=item.get('URL') or 'https://doi.org/' + doi,
            request_url=r['request_url'], retrieved_at=r['retrieved_at'], venue_decision=d))
    return result


def resolve_metadata(raw_row, metadata):
    accepted = [e for e in metadata if e['identity_accepted']]
    direct_rejected = any(not e['identity_accepted'] and e['identifier_binding']['kind'] == 'raw_doi' for e in metadata)
    if direct_rejected:
        return decision('unresolved', 'unknown', 'identifier_identity_review'), None, 'metadata_review'
    if not accepted:
        return decision(raw_row['mapping_status'], raw_row['venue_type'], raw_row['reason'], raw_row['conference_id'] or ''), None, 'raw_mapping'
    labels = {(e['venue_decision']['mapping_status'], e['venue_decision']['venue_type'], e['venue_decision']['conference_id'] or '') for e in accepted}
    if len(labels) != 1 or any(e['venue_decision']['mapping_status'] == 'unresolved' for e in accepted):
        return decision('unresolved', 'unknown', 'publication_metadata_review'), None, 'metadata_checked'
    status, kind, cid = labels.pop()
    years = {e['publication_year'] for e in accepted if e['publication_year'] is not None}
    return decision(status, kind, 'identifier_metadata_consensus', cid), next(iter(years)) if len(years) == 1 else None, 'metadata_checked'


def rebuild(raw, papers, aliases, mapping, records):
    # Recompute both the original algorithm and expanded raw mapping, never read previous outputs.
    base_map = {venue: dict(r, **classify(venue)) for venue, r in mapping.items()}
    baseline, _, _ = make_records(raw, papers, aliases, base_map)
    expanded, _, _ = make_records(raw, papers, aliases, mapping)
    baseline_by_id = {r['paper_id']: r for r in baseline}
    paper_by_id = {p['paper_id']: p for p in papers}
    by_sid = defaultdict(list)
    for r in records:
        if r['provider'] == 'semantic_scholar':
            sid = r['lookup']['value']
            require(sid in raw and str((r['item'].get('externalIds') or {}).get('CorpusId')) == sid, 'Wrong CorpusId in local cache')
            by_sid[sid].append(r)
    crossref = best_crossref(records)
    links, comparison = [], []
    for r in expanded:
        old = baseline_by_id[r['paper_id']]
        metadata = select_metadata(r, paper_by_id[r['paper_id']], raw, by_sid, crossref, mapping)
        d, year, level = resolve_metadata(r, metadata)
        row = dict(r, conference_id=d['conference_id'] or None, mapping_status=d['mapping_status'], venue_type=d['venue_type'],
            reason=d['rule_id'], verification_level=level, publication_year=year,
            metadata_evidence=metadata, baseline_status=old['mapping_status'], baseline_conference_id=old['conference_id'],
            expanded_raw_status=r['mapping_status'], expanded_raw_conference_id=r['conference_id'])
        links.append(row)
        comparison.append(dict(paper_id=r['paper_id'], baseline_status=old['mapping_status'], baseline_conference_id=old['conference_id'] or '',
            expanded_raw_status=r['mapping_status'], expanded_raw_conference_id=r['conference_id'] or '',
            final_status=row['mapping_status'], final_conference_id=row['conference_id'] or '', verification_level=level,
            changed=(old['mapping_status'], old['conference_id']) != (row['mapping_status'], row['conference_id']), reason=row['reason']))
    grouped = defaultdict(list)
    for r in links:
        if r['mapping_status'] == 'matched':
            grouped[r['conference_id']].append(r['paper_id'])
    catalog, groups = [], []
    for cid in sorted(grouped):
        venue_names = set()
        for r in links:
            if r['conference_id'] != cid:
                continue
            venue_names.update(e['venue_raw'] for e in r['evidence'] if e['conference_id'] == cid)
            venue_names.update(e['venue_raw'] for e in r['metadata_evidence'] if e['identity_accepted'] and e['venue_decision']['conference_id'] == cid)
        catalog.append(dict(conference_id=cid, **REGISTRY[cid], aliases=sorted(venue_names), in_target_catalog=True,
            selection_reason='Observed CSFCube publications; no year/quota/shortlist imposed', registry_sources=[str(MAPPING)], verification_level='mixed'))
        groups.append(dict(conference_id=cid, paper_count=len(grouped[cid]), paper_ids=grouped[cid]))
    require(len(links) == len(papers) and {r['paper_id'] for r in links} == set(paper_by_id), 'Paper coverage error')
    require(all(r['source'] == 'csfcube' and r['edition_year'] is None for r in links), 'Scope/year inferred')
    require(all(all(r[k] == v for k, v in raw_year_fields(r['evidence']).items()) for r in links), 'Final raw years changed')
    flat = [pid for g in groups for pid in g['paper_ids']]
    require(len(flat) == len(set(flat)) and set(flat) == {r['paper_id'] for r in links if r['mapping_status'] == 'matched'}, 'Group membership mismatch')
    require(all((r['conference_id'] in grouped) if r['mapping_status'] == 'matched' else r['conference_id'] is None for r in links), 'Invalid final label')
    return links, catalog, groups, comparison, baseline, expanded


def enriched_self_test():
    count = self_test()
    cases = [('2012 IEEE International Conference on Robotics and Automation', 'matched', 'CONF_ICRA'),
        ('International Conference on Machine Learning and Applications', 'matched', 'CONF_ICMLA'),
        ('AAAI Conference on Artificial Intelligence and Interactive Digital Entertainment', 'matched', 'CONF_AIIDE'),
        ('SIAM International Conference on Data Mining', 'matched', 'CONF_SDM'),
        ('ECML/PKDD', 'matched', 'CONF_ECML_PKDD'), ('WMT', 'unresolved', ''),
        ('Conference on Machine Translation', 'matched', 'CONF_WMT'),
        ('Workshop on Machine Translation', 'excluded', ''), ('ICRA Workshop', 'excluded', ''),
        ('SIGIR Demo', 'excluded', ''), ('Unknown Venue', 'unresolved', '')]
    for name, status, cid in cases:
        d = classify_expanded(name)
        require((d['mapping_status'], d['conference_id']) == (status, cid), 'Expanded classifier regression: ' + name)
    raw_row = dict(mapping_status='matched', venue_type='conference', conference_id='CONF_ACL', reason='raw')
    def ev(cid='CONF_ACL', kind='conference', accepted=True, binding='raw_doi'):
        return dict(identity_accepted=accepted, identifier_binding=dict(kind=binding), publication_year=2015,
                    venue_decision=decision('matched' if kind == 'conference' else 'excluded', kind, 'test', cid))
    require(resolve_metadata(raw_row, [ev(kind='workshop', cid='')])[0]['mapping_status'] == 'excluded', 'Workshop must override umbrella raw label')
    require(resolve_metadata(raw_row, [ev(), ev(kind='journal', cid='')])[0]['mapping_status'] == 'unresolved', 'Different publication types must remain unresolved')
    require(resolve_metadata(raw_row, [ev(accepted=False)])[0]['mapping_status'] == 'unresolved', 'Wrong direct DOI identity must not silently retain label')
    require(resolve_metadata(raw_row, [ev(accepted=False, binding='corpus_id_to_doi')])[0]['conference_id'] == 'CONF_ACL', 'Untrusted discovery must not override raw')
    require(title_key('A Study: Café') == title_key('A study cafe'), 'Title normalization failed')
    require(title_key('Effect on A') != title_key('Effect on B'), 'Different titles collapsed')
    require(authors_check([dict(first='John', last='Smith')], [dict(given='Alice', family='Jones')]) == 'mismatched', 'Authors mismatch accepted')
    require(authors_check([dict(first='John', last='Smith')], []) == 'unavailable', 'Missing authors called matched')
    require(doi_key('https://doi.org/10.1234/ABC') == '10.1234/abc', 'DOI normalization failed')
    # End-to-end identity gates using synthetic API records, not implementation-only mirrors.
    sid, doi = '12345', '10.1234/example'
    title = 'A sufficiently distinctive research paper title'
    native = dict(title=title, metadata=dict(doi=doi, authors=[dict(first='Alice', last='Nguyen')]))
    fake_raw = {sid: (1, native)}
    fake_row = dict(source_ids=[sid])
    fake_paper = dict(title=title)
    fake_mapping = {'ACL': classify_expanded('ACL')}
    fake_item = dict(DOI=doi, title=[title], **{'container-title': ['ACL']}, type='proceedings-article')
    response = dict(url='https://api.crossref.org/works/' + doi, retrieved_at='2026-10-30T00:00:00+00:00')
    record = cache_record('crossref', dict(kind='doi', value=doi), fake_item, response, dict(path='fixture', sha256='fixture'))
    selected = select_metadata(fake_row, fake_paper, fake_raw, {}, {doi: record}, fake_mapping)
    require(selected[0]['identity_accepted'] and selected[0]['author_check'] == 'unavailable', 'Exact raw DOI/title should explicitly preserve missing author state')
    fake_item['title'] = ['Different research paper title']
    require(not select_metadata(fake_row, fake_paper, fake_raw, {}, {doi: record}, fake_mapping)[0]['identity_accepted'], 'Wrong title accepted via DOI')
    fake_item['title'] = [title]
    fake_item['author'] = [dict(given='Bob', family='Smith')]
    require(not select_metadata(fake_row, fake_paper, fake_raw, {}, {doi: record}, fake_mapping)[0]['identity_accepted'], 'Wrong authors accepted via DOI')
    fake_item['author'] = [dict(given='Alice', family='Nguyen')]
    native['metadata']['doi'] = None
    s2 = dict(record_id='connector', item=dict(title=title, externalIds=dict(DOI=doi, CorpusId=int(sid))))
    selected = select_metadata(fake_row, fake_paper, fake_raw, {sid: [s2]}, {doi: record}, fake_mapping)
    require(selected[0]['identity_accepted'] and selected[0]['identifier_binding']['kind'] == 'corpus_id_to_doi', 'Anchored CorpusId DOI chain failed')
    fake_item.pop('author')
    require(not select_metadata(fake_row, fake_paper, fake_raw, {sid: [s2]}, {doi: record}, fake_mapping)[0]['identity_accepted'], 'Discovered DOI accepted without author corroboration')
    require(select_metadata(fake_row, fake_paper, fake_raw, {sid: [s2]}, {}, fake_mapping) == [], 'Index-only record became publication metadata')
    fake_item['author'] = [dict(given='Alice', family='Nguyen')]
    fake_item['type'] = 'journal-article'
    require(select_metadata(fake_row, fake_paper, fake_raw, {sid: [s2]}, {doi: record}, fake_mapping)[0]['venue_decision']['mapping_status'] == 'unresolved', 'Unexpected registration type silently accepted as conference')
    return count + len(cases) + 16


def csv_text(rows):
    import io
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return '\ufeff' + stream.getvalue()


def enriched_report(links, groups, catalog, comparison, baseline, expanded, cache_manifest):
    before = Counter(r['mapping_status'] for r in baseline)
    middle = Counter(r['mapping_status'] for r in expanded)
    after = Counter(r['mapping_status'] for r in links)
    added = sum(r['baseline_status'] != 'matched' and r['final_status'] == 'matched' for r in comparison)
    removed = sum(r['baseline_status'] == 'matched' and r['final_status'] != 'matched' for r in comparison)
    changed_cid = sum(r['baseline_status'] == r['final_status'] == 'matched' and r['baseline_conference_id'] != r['final_conference_id'] for r in comparison)
    conf = [r for r in links if r['mapping_status'] == 'matched']
    with_metadata = sum(r['verification_level'] == 'metadata_checked' for r in conf)
    with_authors = sum(any(e['identity_accepted'] and e['author_check'] == 'matched' for e in r['metadata_evidence']) for r in conf)
    lines = ['# Kết quả mở rộng mapping CSFCube', '',
        'Chạy lại từ raw + corpus/ID chung + bảng mapping + cache metadata cục bộ. Không đọc output hoặc nhãn cũ của Extra_DOING; không gọi LLM.', '',
        '| Trạng thái | Bản 1: raw mapping | Mở rộng tên raw | Bản 2: thêm metadata định danh |', '|---|---:|---:|---:|']
    lines += [f'| {s} | {before[s]} | {middle[s]} | {after[s]} |' for s in ('matched', 'excluded', 'unresolved')]
    lines += ['', f'Tổng: **{len(links)} bài CSFCube**. Conference/joint IDs cuối: **{len(catalog)}**.', '',
        f'- Bài mới vào conference: **{added}**; bài rời conference: **{removed}**; bài còn conference nhưng đổi ID: **{changed_cid}**.',
        '- Không cộng nhãn cũ vào nhãn mới. Metadata có thể sửa raw conference thành workshop/journal hoặc giữ chưa rõ.',
        '- DOI gốc được tra đúng định danh; DOI từ Semantic Scholar chỉ dùng khi nối đúng CorpusId/title và Crossref đối chiếu được tác giả.',
        '- Chỉ title chuẩn hóa trùng hoàn toàn mới nhận metadata. Thiếu tác giả được ghi rõ, không gọi là đã kiểm tra tác giả đạt.',
        f'- Trong nhóm conference: **{with_metadata} bài** có metadata được nhận; **{len(conf)-with_metadata} bài** còn dựa trên raw mapping. **{with_authors} bài** có đối chiếu tác giả đạt theo quy tắc tự động.',
        '- Nhiều DOI/bản công bố có loại hoặc conference khác nhau giữ unresolved; không chọn nhãn thuận lợi để tăng số bài.', '',
        '## Nguồn và giới hạn', '',
        f"Cache chứa {cache_manifest['records']} phản hồi bài/metadata từ API theo định danh (có thể nhiều snapshot cho một DOI). Cache là đầu vào có hash, không phải bảng nhãn được nhập sẵn.",
        'Mặc định chạy offline. Cache ban đầu được tái sử dụng từ các evidence_cache cũ; có lưu URL/thời điểm/hash nguồn. Không sử dụng tìm title hoặc lần ngược arXiv. '
        'Các lựa chọn tên/alias vẫn là quy tắc cục bộ, chưa được người chấm xác nhận toàn bộ. Chưa đo precision/recall nhãn; chưa có human gold.', '',
        '## Số bài theo hội nghị', '', '| ID | Hội nghị | Số bài |', '|---|---|---:|']
    names = {r['conference_id']: r['canonical_name'] for r in catalog}
    lines += [f"| {g['conference_id']} | {names[g['conference_id']]} | {g['paper_count']} |" for g in sorted(groups, key=lambda g: (-g['paper_count'], g['conference_id']))]
    lines += ['', 'Xem `comparison.csv` để đối chiếu từng bài; `paper_conference_links.jsonl` để xem raw và metadata hỗ trợ/bị loại. '
              'Chưa áp quota, chưa chọn shortlist, chưa chia tập hoặc xây profile.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-cache', metavar='EXTRA_DOING', help='Bootstrap local metadata from original API responses, never labels; then run the full pipeline')
    parser.add_argument('--prepare-mapping', action='store_true', help='Add newly observed names/counts while preserving stage-2 mapping decisions')
    parser.add_argument('--fetch-missing', action='store_true', help='Explicit optional Crossref exact-DOI refresh; default is offline')
    parser.add_argument('--limit', type=int, default=50, help='Maximum refresh requests; 0 means all missing DOI records')
    parser.add_argument('--check', action='store_true', help='Recompute everything and verify outputs without writing')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--output-dir', type=Path, help='Alternative output directory for a clean reproducibility check')
    args = parser.parse_args()
    require(args.limit >= 0, 'Limit must be nonnegative')
    require(not args.check or not (args.import_cache or args.prepare_mapping or args.fetch_missing), '--check must not mutate inputs')
    tests = enriched_self_test()
    if args.self_test:
        print(json.dumps(dict(self_tests_passed=tests)))
        return
    core_hashes = {k: sha(p) for k, p in INPUTS.items()}
    raw, papers, aliases = load_inputs()
    if args.import_cache:
        import_identifier_cache(args.import_cache, raw)
    if args.fetch_missing and not CACHE_DATA.exists():
        save_cache([], [])
    records, cache_manifest = load_cache()
    network_requests = 0
    if args.fetch_missing:
        network_requests = fetch_missing(raw, records, cache_manifest, args.limit)
        records, cache_manifest = load_cache()
    mapping = expanded_mapping(raw, aliases, records, prepare=bool(args.prepare_mapping or args.import_cache or args.fetch_missing))
    inputs = dict(INPUTS, mapping=MAPPING, metadata_cache=CACHE_DATA, cache_manifest=CACHE_MANIFEST, script=Path(__file__).resolve())
    hashes = {k: sha(p) for k, p in inputs.items()}
    require(all(hashes[k] == value for k, value in core_hashes.items()), 'Shared input changed after loading')
    links, catalog, groups, comparison, baseline, expanded = rebuild(raw, papers, aliases, mapping, records)
    report = enriched_report(links, groups, catalog, comparison, baseline, expanded, cache_manifest)
    files = {'paper_conference_links.jsonl': links, 'conference_catalog.jsonl': catalog, 'conference_papers.jsonl': groups}
    require(hashes == {k: sha(p) for k, p in inputs.items()}, 'Inputs changed during rebuild')
    out = args.output_dir.resolve() if args.output_dir else OUT
    require(out.is_relative_to(HERE) and out != HERE and not out.is_relative_to(CACHE),
            'Outputs must stay in a separate directory inside stage 2, outside the cache')
    if args.check:
        manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
        require(manifest['input_hashes'] == hashes, 'Input/code/cache differs from saved output')
        for name, rows in files.items():
            require(read_jsonl(out / name) == rows, 'Deterministic rebuild differs: ' + name)
        require((out / 'report.md').read_text(encoding='utf-8') == report, 'Report differs')
        require((out / 'comparison.csv').read_bytes() == csv_text(comparison).encode('utf-8'), 'Comparison differs')
        require(all(sha(out / name) == digest for name, digest in manifest['output_hashes'].items()), 'Output hash mismatch')
        require(manifest['counts']['statuses'] == dict(Counter(r['mapping_status'] for r in links)), 'Manifest count mismatch')
        print(json.dumps(dict(check='passed', self_tests_passed=tests, papers=len(links), deterministic_rebuild=True)))
        return
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in files.items():
        write_jsonl(out / name, rows)
    (out / 'report.md').write_text(report, encoding='utf-8')
    (out / 'comparison.csv').write_bytes(csv_text(comparison).encode('utf-8'))
    manifest = dict(schema_version=VERSION, dataset_version=VERSION, source='csfcube',
        generated_at=datetime.now(timezone.utc).isoformat(), network_requests=network_requests, llm_calls=0,
        human_paper_review_performed=False, old_labels_used=False, external_legacy_code_used=False,
        input_paths={k: str(p) for k, p in inputs.items()}, input_hashes=hashes,
        counts=dict(raw_records=len(raw), canonical_papers=len(papers), conferences=len(catalog),
            statuses=dict(Counter(r['mapping_status'] for r in links)),
            year_statuses=dict(Counter(r['year_status'] for r in links)),
            matched_with_year=sum(r['mapping_status']=='matched' and r['year'] is not None for r in links),
            baseline_statuses=dict(Counter(r['mapping_status'] for r in baseline)),
            expanded_raw_statuses=dict(Counter(r['mapping_status'] for r in expanded)),
            verification_levels=dict(Counter(r['verification_level'] for r in links)),
            reasons=dict(Counter(r['reason'] for r in links)),
            added_conference=sum(r['baseline_status'] != 'matched' and r['final_status'] == 'matched' for r in comparison),
            removed_conference=sum(r['baseline_status'] == 'matched' and r['final_status'] != 'matched' for r in comparison),
            changed_conference_id=sum(r['baseline_status'] == r['final_status'] == 'matched' and r['baseline_conference_id'] != r['final_conference_id'] for r in comparison)),
        checks=dict(self_tests_passed=tests, source_and_alias_integrity=True, inputs_unchanged=True,
            local_cache_hash_verified=True, all_stages_recomputed=True, semantic_label_accuracy='not_measured'),
        output_hashes={name: sha(out / name) for name in [*files, 'report.md', 'comparison.csv']})
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest['counts'], ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
