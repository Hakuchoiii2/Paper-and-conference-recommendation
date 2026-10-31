"""Build a public venue directory for raw-name mapping; never search for papers."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import time
import unicodedata
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
REVIEW = HERE / "review"
SOURCES = REVIEW / "venue_sources.jsonl"
DIRECTORY = REVIEW / "venue_directory.jsonl"
MANIFEST = REVIEW / "catalog_manifest.json"
RAW = PROJECT / "data/raw/csfcube/abstracts-csfcube-preds.jsonl"
ROUNDS = ["ICORE2026", "CORE2023", "CORE2018", "CORE2014"]
ACL_DIRECTORY = 'https://aclanthology.org/'


class ACLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.current=None;self.acronym=False

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a' and re.fullmatch(r'/venues/[^/]+/',attrs.get('href','')):
            self.current=dict(href=attrs['href'],name=attrs.get('title',''),acronym='')
        if self.current and tag=='span' and 'acl-venue-row__acronym' in attrs.get('class',''):
            self.acronym=True

    def handle_data(self,data):
        if self.current and self.acronym:self.current['acronym']+=data

    def handle_endtag(self,tag):
        if tag=='span':self.acronym=False
        if tag=='a' and self.current:
            if self.current['name'] and self.current['acronym']:self.rows.append(self.current)
            self.current=None


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def key(value):
    t = unicodedata.normalize("NFKD", html.unescape(value or "")).casefold()
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"['’]\s*\d{2}\b", " ", t)
    t = re.sub(r"\b(?:1[89]|20)\d{2}\b|\b\d+(?:st|nd|rd|th)\b", " ", t)
    t = t.replace("&", " and ")
    t = re.sub(r"[^\w@*]+", " ", t, flags=re.UNICODE).replace("_", " ")
    t = " ".join(t.split())
    t = re.sub(r"^(?:in )?(?:proceedings? (?:of )?(?:the )?|proc )", "", t)
    t = re.sub(r"^(?:the )?(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth) (?=international|annual|conference|symposium)", "", t)
    while re.match(r"^(?:acm|ieee|wic) .+", t):
        t = t.split(" ", 1)[1]
    return t


def aliases(name, acronym=""):
    result = {key(name)}
    if acronym:
        result.add(key(acronym))
    # Only remove a trailing parenthesized acronym when the complete remaining title matches.
    result.add(key(re.sub(r"\s*\([^()]*\)\s*$", "", name)))
    return result - {""}


def fetch(url, provider, lookup):
    rec = dict(provider=provider, request_url=url, lookup=lookup,
               retrieved_at=datetime.now(timezone.utc).isoformat())
    try:
        if provider == 'crossref_journals':
            time.sleep(1.0)
        request = urllib.request.Request(url, headers={"User-Agent": "ConferenceDatasetResearch/1.0", "Accept": "application/json,text/csv"})
        with urllib.request.urlopen(request, timeout=25) as stream:
            text = stream.read().decode("utf-8-sig")
            rec.update(status_code=stream.status, content_type=stream.headers.get("Content-Type"), response_text=text)
        if provider == "crossref_journals":
            json.loads(text)
        elif provider == 'acl_directory':
            parser=ACLParser();parser.feed(text)
            if not parser.rows:raise ValueError('No recognizable ACL venue directory')
        elif provider == 'icore' and (rec["status_code"] != 200 or "<html" in text[:200].lower()):
            raise ValueError("Expected an official CSV export")
    except Exception as exc:
        rec["error"] = type(exc).__name__ + ": " + str(exc)
        if getattr(exc, 'code', None) == 429:
            rec['retry_after'] = exc.headers.get('Retry-After')
    return rec


def directory(responses):
    entries = {}
    for response in responses.values():
        if response.get("error"):
            continue
        if response["provider"] == "icore":
            for row in csv.reader(io.StringIO(response["response_text"])):
                if len(row) < 5 or not row[0].strip().isdigit() or row[3].strip() != response["lookup"]:
                    continue
                ident = "icore:" + row[0].strip()
                title, acronym = row[1].strip(), row[2].strip()
                # A ranking directory also includes workshops: do not turn those into main conferences.
                kind = "workshop" if re.search(r"\bworkshops?\b", title, re.I) else "conference"
                if re.search(r"\bjournal\b|\btransactions\b", title, re.I):
                    kind = "journal"
                item = entries.setdefault(ident, dict(catalog_id=ident, provider="icore", canonical_name=title,
                    acronym=acronym, names=[], acronyms=[], kinds=[], source_urls=[]))
                item["names"].append(title)
                item["acronyms"].append(acronym)
                item["kinds"].append(kind)
                item["source_urls"].extend([response["request_url"], "https://portal.core.edu.au/conf-ranks/" + row[0].strip() + "/"])
        elif response["provider"] == "crossref_journals":
            payload = json.loads(response["response_text"])
            for row in payload.get("message", {}).get("items", []):
                title = row.get("title") or ""
                alternatives = row.get("alternative-title") or []
                if isinstance(alternatives, str):
                    alternatives = [alternatives]
                # Search only discovers candidates; require a complete normalized title match.
                if key(response["lookup"]) not in {key(n) for n in [title, *alternatives]}:
                    continue
                issns = sorted(row.get("ISSN") or [])
                if not issns:
                    continue
                ident = "crossref_journal:" + issns[0]
                item = entries.setdefault(ident, dict(catalog_id=ident, provider="crossref_journals",
                    canonical_name=title, acronym="", names=[], acronyms=[], kinds=["journal"], source_urls=[]))
                item["names"].extend([title, *alternatives])
                item["source_urls"].append(response["request_url"])
        elif response['provider']=='acl_directory':
            parser=ACLParser();parser.feed(response['response_text'])
            for row in parser.rows:
                title=row['name'];low=title.casefold()
                kind='workshop' if re.search(r'\bworkshop\b',low) else 'conference' if re.search(r'\bconference\b|\bsymposium\b|\bmeeting\b',low) else 'journal' if re.search(r'\bjournal\b|\btransactions\b',low) else 'auxiliary' if re.search(r'\bshared task\b|\bstudent research\b|\bdemonstration',low) else 'unknown'
                ident='acl:'+row['href'].strip('/').split('/')[-1]
                entries[ident]=dict(catalog_id=ident,provider='acl_directory',canonical_name=title,acronym=row['acronym'].strip(),
                    names=[title],acronyms=[row['acronym'].strip()],kinds=[kind],source_urls=[ACL_DIRECTORY.rstrip('/')+row['href'],response['request_url']])
    for item in entries.values():
        for field in ["names", "acronyms", "kinds", "source_urls"]:
            item[field] = sorted(set(item[field]) - {""})
        item["venue_type"] = item["kinds"][0] if len(item["kinds"]) == 1 else "unknown"
    # Merge only cross-provider records with the same full normalized name,
    # acronym and event kind, retaining both primary sources.
    core = defaultdict(list)
    for row in entries.values():
        if row['provider']=='icore':
            for n in row['names']:
                for a in row['acronyms']:core[(key(n),key(a),row['venue_type'])].append(row)
    redundant=[]
    for ident,row in entries.items():
        if row['provider']=='acl_directory':
            peers=core.get((key(row['canonical_name']),key(row['acronym']),row['venue_type']),[])
            peers={p['catalog_id']:p for p in peers}
            if len(peers)==1:
                peer=next(iter(peers.values()));peer['source_urls']=sorted(set(peer['source_urls']+row['source_urls']));redundant.append(ident)
    for ident in redundant:del entries[ident]
    return sorted(entries.values(), key=lambda r: r["catalog_id"])


def index_directory(rows):
    index = defaultdict(dict)
    for row in rows:
        # Very short journal acronyms are not inferred from full titles.
        keys = set()
        for name in row["names"]:
            keys |= aliases(name)
        for acronym in row["acronyms"]:
            keys |= aliases(acronym)
        for k in keys:
            index[k][row["catalog_id"]] = row
    return {k: list(v.values()) for k, v in index.items()}


def lookup(venue, index):
    normalized = key(venue)
    if re.search(r"\bcompanion\b|\badjunct\b|\bsupplement\b|\bposters?\b|\bdoctoral\b|\blate.breaking\b|instruction file|wspc/", venue, re.I):
        return [], "track_or_noise_review"
    matches = index.get(normalized, [])
    if not matches and "(" in venue:
        tail = re.fullmatch(r"(.*?)\s*\(([^()]+)\)\s*", venue)
        if tail:
            body = index.get(key(tail[1]), [])
            suffix_ids = {r['catalog_id'] for r in index.get(key(tail[2]), [])}
            matches = [r for r in body if r['catalog_id'] in suffix_ids]
    if not matches and "@" in venue:
        # Identify the child venue, never substitute its conference host.
        children = index.get(key(venue.split("@", 1)[0]), [])
        matches = [r for r in children if r["venue_type"] in {'workshop','conference','auxiliary'}]
    if len(matches) != 1:
        return [], "ambiguous_directory_name" if matches else "unlisted_venue"
    row = matches[0]
    # These series changed event type or have main/shared-task ambiguity over time.
    if key(venue.split('@',1)[0]) in {"wmt", "iwcs"}:
        return [], "historical_track_review"
    if row["venue_type"] == "unknown":
        return [], "historical_event_kind_review"
    return matches, "directory_collocated_child" if '@' in venue and not index.get(normalized) else "directory_exact_name"


def journal_queries(raw, index):
    values = sorted({(r.get("metadata") or {}).get("venue") or "" for r in raw})
    queries = []
    for value in values:
        k = key(value)
        if len(k) < 8 or len(k.split()) < 2 or "@" in value or lookup(value, index)[0]:
            continue
        if re.search(r"conference|symposium|workshop|proceeding|colloquium|congress|\barxiv\b|\bcorr\b|instruction|\bchapter\b|\bmeeting\b|shared task", k):
            continue
        queries.append(value)
    return queries


def prepare(download=False):
    REVIEW.mkdir(exist_ok=True)
    responses = {r["request_url"]: r for r in load(SOURCES)}
    count = 0
    for round_name in ROUNDS:
        url = "https://portal.core.edu.au/conf-ranks/?" + urllib.parse.urlencode(dict(search="", by="all", source=round_name, do="Export"))
        if download and (url not in responses or responses[url].get("error")):
            responses[url] = fetch(url, "icore", round_name)
            count += 1
            write(SOURCES, sorted(responses.values(), key=lambda r: r["request_url"]))
        if url not in responses:
            raise ValueError("Run --download-sources once to obtain the public venue directory")
    if download and (ACL_DIRECTORY not in responses or responses[ACL_DIRECTORY].get('error')):
        responses[ACL_DIRECTORY]=fetch(ACL_DIRECTORY,'acl_directory','all_venues');count+=1
        write(SOURCES,sorted(responses.values(),key=lambda r:r['request_url']))
    rows = directory(responses)
    if not any(r["provider"] == "icore" for r in rows):
        raise ValueError("No usable official conference directory; refusing to guess names")
    raw = load(RAW)
    queries = journal_queries(raw, index_directory(rows))
    pending = []
    for value in queries:
        url = "https://api.crossref.org/journals?" + urllib.parse.urlencode(dict(query=value, rows=3))
        if download and (url not in responses or responses[url].get("error")):
            pending.append((url, value))
    if pending:
        print("Journal directory queries: " + str(len(pending)), flush=True)
        # Crossref's public pool permits only one simultaneous request.
        with ThreadPoolExecutor(max_workers=1) as pool:
            jobs = {pool.submit(fetch, url, "crossref_journals", value): url for url, value in pending}
            for n, job in enumerate(as_completed(jobs), 1):
                response = job.result()
                responses[response["request_url"]] = response
                count += 1
                if n % 30 == 0 or n == len(jobs):
                    write(SOURCES, sorted(responses.values(), key=lambda r: r["request_url"]))
                    print("Source responses " + str(n) + " / " + str(len(jobs)), flush=True)
    write(SOURCES, sorted(responses.values(), key=lambda r: r["request_url"]))
    rows = directory(responses)
    write(DIRECTORY, rows)
    manifest = dict(mode="external_venue_directory_not_paper_enrichment", llm_calls=0,
        paper_searches=0, arxiv_lookups=0, network_requests=count,
        entries=len(rows), providers={p: sum(r["provider"] == p for r in rows) for p in ["icore", "crossref_journals", "acl_directory"]},
        failed_responses=sum(bool(r.get("error")) for r in responses.values()),
        input_hashes=dict(raw=sha(RAW), sources=sha(SOURCES), script=sha(Path(__file__))),
        directory_sha256=sha(DIRECTORY))
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest), flush=True)


def load_checked():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = dict(raw=sha(RAW), sources=sha(SOURCES), script=sha(Path(__file__)))
    if manifest["input_hashes"] != expected or manifest["directory_sha256"] != sha(DIRECTORY):
        raise ValueError("Venue directory inputs changed; rebuild audit_mapping.py offline")
    return load(DIRECTORY), manifest


def self_test():
    assert key("2012 IEEE 9th International Conference on Example (ICE)") == key("International Conference on Example (ICE)")
    assert key("IUI '03") == key("IUI")
    sample = [dict(catalog_id="icore:1", names=["International Conference on Example"], acronyms=["ICE"],
                   venue_type="conference", canonical_name="International Conference on Example")]
    index = index_directory(sample)
    assert lookup("ICE '03", index)[0]
    assert not lookup("Workshop@ICE", index)[0]
    assert not lookup("ICE Companion", index)[0]
    assert not lookup("International Conference on Example Applications", index)[0]
    assert not lookup("ICE (Poster)", index)[0]
    assert not lookup("International Conference on Example (OTHER)", index)[0]
    assert lookup("International Conference on Example (ICE)", index)[0]
    ambiguous=index_directory(sample+[dict(sample[0],catalog_id='icore:2')])
    assert not lookup('ICE',ambiguous)[0]
    child=dict(sample[0],catalog_id='acl:we',names=['Workshop on Example'],acronyms=['WE'],venue_type='workshop')
    assert lookup('WE@ICE',index_directory(sample+[child]))[0][0]['catalog_id']=='acl:we'
    parser=ACLParser();parser.feed('<a href=/venues/we/ title="Workshop on Example"><span class=acl-venue-row__acronym>WE</span></a>')
    assert parser.rows==[dict(href='/venues/we/',name='Workshop on Example',acronym='WE')]
    return 12


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-sources", action="store_true", help="Explicitly retrieve missing public directory responses; no paper searches")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    self_test()
    if args.check:
        rows, manifest = load_checked()
        print(json.dumps(dict(directory_check="passed", entries=len(rows))))
    else:
        prepare(args.download_sources)
