"""Source-assisted alias audit and seeded paper sample; never labels human gold."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import random
import re
import runpy
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJECT = HERE.parents[2]
BASE = ROOT / '1_raw_mapping'
REVIEW = HERE / 'review'
CACHE = REVIEW / 'source_cache.jsonl'
SEED = 20261030
PER_CONFERENCE = 5
REFERENCES = {
 'ACL': ['https://aclanthology.org/venues/acl/'],
 'EMNLP': ['https://aclanthology.org/venues/emnlp/'],
 'NAACL': ['https://aclanthology.org/venues/naacl/'],
 'EACL': ['https://aclanthology.org/venues/eacl/'],
 'COLING': ['https://aclanthology.org/venues/coling/'],
 'IJCNLP': ['https://aclanthology.org/venues/ijcnlp/'],
 'CONLL': ['https://aclanthology.org/venues/conll/'],
 'LREC': ['https://aclanthology.org/venues/lrec/'],
 'RANLP': ['https://aclanthology.org/venues/ranlp/'],
 'SIGDIAL': ['https://aclanthology.org/venues/sigdial/'],
 'ICML': ['https://proceedings.mlr.press/v80/'],
 'ICLR': ['https://iclr.cc/', 'https://www.iclr.cc/archive/2014/conference-proceedings/', 'https://www.iclr.cc/archive/www/2015.html'],
 'NEURIPS': ['https://proceedings.neurips.cc/'],
 'AAAI': ['https://ojs.aaai.org/index.php/AAAI'],
 'IJCAI': ['https://ijcai.org/all_proceedings/'],
 'KDD': ['https://kdd.org/'],
 'SIGIR': ['https://sigir.org/general-information/history/'],
 'CIKM': ['https://sigir.org/general-information/fact-sheet/'],
 'CVPR': ['https://cvpr.thecvf.com/'],
 'ICCV': ['https://iccv.thecvf.com/'],
 'ECCV': ['https://www.ecva.net/'],
 'ACM_MM': ['https://www.acmmm.org/index.html', 'https://www.sigmm.org/'],
 'ICASSP': ['https://2025.ieeeicassp.org/'],
 'ICPR': ['https://iapr.org/conferences/international-conference-on-pattern-recognition/'],
 'CHI': ['https://chi2024.acm.org/'],
 'WWW': ['https://www.iw3c2.org/conferences/'],
 'WSDM': ['https://www.wsdm-conference.org/'],
 'SIGMOD': ['https://sigmod.org/'],
 'CICLING': ['https://www.cicling.org/2018/'],
 'ICALP': ['https://icalppodcspaa2026.cs.rhul.ac.uk/icalp/'],
 'ACL_IJCNLP': ['https://aclanthology.org/P15-1000/'],
 'COLING_ACL': ['https://aclanthology.org/P06-2000/', 'https://2006.aclweb.org/'],
 'EMNLP_CONLL': ['https://aclanthology.org/D07-1000/'],
 'ECML_PKDD': ['https://ecmlpkdd.org/'],
 'EMNLP_VLC': ['https://aclanthology.org/W99-0600/'],
 'PRIME': ['https://api.crossref.org/works/10.1109%2FICPRIME.2013.6496446'],
}
# Independent, conservative interpretation of publication titles, not the production classifier.
TITLE_PATTERNS = {
 'ACL': r'annual meeting.*association.*computational linguistics|\bacl\b',
 'EMNLP': r'empirical methods in natural language processing|\bemnlp\b',
 'NAACL': r'north american chapter|nations of the americas chapter|\bnaacl\b',
 'EACL': r'european chapter|\beacl\b', 'COLING': r'international conference on computational linguistics|\bcoling\b',
 'IJCNLP': r'international joint conference on natural language processing|\bijcnlp\b',
 'CONLL': r'computational natural language learning|\bconll\b',
 'LREC': r'language resources and evaluation|\blrec\b', 'RANLP': r'recent advances in natural language processing|\branlp\b',
 'SIGDIAL': r'discourse and dialogue|\bsigdial\b', 'ICML': r'international conference on machine learning|\bicml\b',
 'ICLR': r'learning representations|\biclr\b', 'NEURIPS': r'neural information processing systems|\bnips\b|\bneurips\b',
 'AAAI': r'aaai conference on artificial intelligence|national conference on artificial intelligence|\baaai\b',
 'IJCAI': r'international joint conference on artificial intelligence|\bijcai\b',
 'KDD': r'knowledge discovery and data mining|\bsigkdd\b|\bkdd\b',
 'SIGIR': r'research and development in information retrieval|research .* development on information retrieval|\bsigir\b',
 'CIKM': r'information and knowledge management|information & knowledge management|\bcikm\b',
 'CVPR': r'computer vision and pattern recognition|\bcvpr\b',
 'ICCV': r'international conference on computer vision|\biccv\b', 'ECCV': r'european conference on computer vision|\beccv\b',
 'ACM_MM': r'acm.*multimedia|multimedia.*\bmm\b', 'ICASSP': r'acoustics.*speech.*signal processing|\bicassp\b',
 'ICPR': r'international conference on pattern recognition|\bicpr\b',
 'CHI': r'human factors in computing systems|\bchi\b', 'WWW': r'world wide web|\bwww\b|the web conference',
 'WSDM': r'web search and data mining|\bwsdm\b', 'SIGMOD': r'management of data|\bsigmod\b',
 'CICLING': r'computational linguistics and intelligent text processing|\bcicling\b',
 'ICALP': r'automata.*languages.*programming|\bicalp\b', 'ECML_PKDD': r'ecml.*pkdd|machine learning and knowledge discovery in databases',
}
PROGRAMS = {
 'https://www.iclr.cc/archive/2014/conference-proceedings/': ('CONF_ICLR','conference'),
 'https://www.iclr.cc/archive/www/2015.html': ('CONF_ICLR','headings'),
}
EXACT_PAPER_URLS = {
 'P002473': ['https://api.openreview.net/notes?id=H1aIuk-RW'],
}
ENRICHED_PATTERNS = {
 'INTERSPEECH':r'\binterspeech\b','ICDM':r'ieee.*conference on data mining|\bicdm\b',
 'ICME':r'conference on multimedia and expo','ICRA':r'conference on robotics and automation',
 'IROS':r'conference on intelligent robots and systems','ICWSM':r'conference on web and social media',
 'ICMLA':r'conference on machine learning and applications','ICMLC':r'conference on machine learning and cybernetics',
 'ICSC':r'conference on semantic computing','ICFHR':r'conference on frontiers in handwriting recognition',
 'WACV':r'conference on applications of computer vision','IJCNN':r'joint conference on neural networks',
 'CIG':r'conference on computational intelligence and games','SMC':r'conference on systems[,]? man[,]? and cybernetics',
 'COMPSAC':r'computer software and applications conference','ASONAM':r'advances in social networks analysis and mining',
 'BIGDATA':r'conference on big data','ECIR':r'european conference on information retrieval',
 'TSD':r'conference on text[,]? speech[,]? and dialogue','AISTATS':r'conference on artificial intelligence and statistics',
 'CSCW':r'conference on computer[- ]supported cooperative work','UIST':r'symposium on user interface software and technology',
 'SODA':r'symposium on discrete algorithms','GECCO':r'genetic and evolutionary computation conference|conference on genetic and evolutionary computation',
 'HT':r'conference on hypertext','WEBSCI':r'web science conference','PACLIC':r'pacific asia conference on language[,]? information and computation',
 'AMTA':r'conference.*machine translation in the americas','MICCAI':r'medical image computing and computer[- ]assisted intervention',
 'ECML':r'european conference on machine learning','WMT':r'conference on machine translation',
 'ICDAR':r'conference on document analysis and recognition','ICSE':r'conference on software engineering',
 'ICDE':r'conference on data engineering','ICIP':r'conference on image processing','ICTAI':r'conference on tools with artificial intelligence',
 'FOCS':r'symposium on foundations of computer science','STOC':r'symposium on theory of computing',
 'SAC':r'symposium on applied computing','SDM':r'siam.*conference on data mining','ESWC':r'extended semantic web conference',
 'NLPCC_ICCPOL':r'nlpcc.*iccpol',
}


def load(path):
    with path.open(encoding='utf-8-sig') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(value):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', html.unescape(value or '')).casefold() if c.isalnum())


def doi_key(value):
    return re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', str(value or '').strip(), flags=re.I).casefold()


def get(url):
    record = dict(url=url, retrieved_at=datetime.now(timezone.utc).isoformat())
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ConferenceDatasetSourceAudit/1.0 (public metadata; no title search)'})
        with urllib.request.urlopen(req, timeout=25) as response:
            body = response.read(2_000_001)
            record.update(ok=True, final_url=response.url, body_sha256=hashlib.sha256(body).hexdigest(),
                          truncated=len(body)>2_000_000, text=body[:2_000_000].decode('utf-8', errors='replace'))
    except Exception as error:
        record.update(ok=False, error=str(error))
    return record


def save_cache(cache):
    REVIEW.mkdir(exist_ok=True)
    CACHE.write_text(''.join(json.dumps(cache[url], ensure_ascii=False, sort_keys=True)+'\n' for url in sorted(cache)), encoding='utf-8')


def fetch_urls(urls, cache):
    pending = sorted(set(urls)-set(cache))
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(get,url):url for url in pending}
        for i,f in enumerate(as_completed(futures),1):
            cache[futures[f]]=f.result()
            if i%20==0 or i==len(pending):
                print('Source responses',i,'/',len(pending),flush=True)
    save_cache(cache)
    return len(pending)


def paper_urls(row, raw, old_cache):
    dois=set(); acl=set()
    for sid in row['source_ids']:
        md=raw[sid].get('metadata') or {}
        if md.get('doi'): dois.add(doi_key(md['doi']))
        if md.get('acl_id'):
            aid=md['acl_id']
            aid=aid.upper() if re.fullmatch(r'[A-Za-z]\d{2}-\d{4}',aid) else aid.lower()
            acl.add('https://aclanthology.org/'+aid+'.bib')
    if not dois:
        for r in old_cache:
            if r['provider']=='semantic_scholar' and r['lookup']['value'] in row['source_ids']:
                doi=doi_key((r['item'].get('externalIds') or {}).get('DOI'))
                if doi and key(r['item'].get('title'))==key(row['title']): dois.add(doi)
    urls=['https://api.crossref.org/works/'+urllib.parse.quote(d,safe='') for d in sorted(dois)]
    return urls+sorted(acl)


def bib_field(text,name):
    match=re.search(r'\b'+re.escape(name)+r'\s*=\s*([{"])',text,re.I)
    if not match:return ''
    start=match.end(); level=1 if match[1]=='{' else 0
    for end in range(start,len(text)):
        c=text[end]
        if match[1]=='"':
            if c=='"' and (end==0 or text[end-1]!='\\'):break
            continue
        if c=='{' and (end==0 or text[end-1]!='\\'):level+=1
        elif c=='}' and (end==0 or text[end-1]!='\\'):
            level-=1
            if level==0:break
    return html.unescape(text[start:end].replace('{','').replace('}',''))


def metadata(response):
    if not response.get('ok'):return None
    if 'api.crossref.org' in response['url']:
        try: work=json.loads(response['text'])['message']
        except (ValueError,KeyError):return None
        if not isinstance(work,dict) or not work.get('DOI'):return None
        return dict(title=' '.join(work.get('title') or []),venue='; '.join(work.get('container-title') or []),
                    authors=[a.get('family','') for a in work.get('author') or []],type=work.get('type',''),doi=work['DOI'])
    if response['url'].endswith('.bib'):
        title=bib_field(response['text'],'title')
        venue=bib_field(response['text'],'booktitle') or bib_field(response['text'],'journal')
        if not title:return None
        authors=[a.strip().split(',')[0] for a in re.split(r'\s+and\s+',bib_field(response['text'],'author'))]
        return dict(title=title,venue=venue,authors=authors,type='anthology_bib',doi=bib_field(response['text'],'doi'))
    if response['url'].startswith('https://api.openreview.net/notes?'):
        try:notes=json.loads(response['text']).get('notes',[])
        except ValueError:return None
        if len(notes)!=1:return None
        content=notes[0].get('content') or {}
        value=lambda k:content.get(k,{}).get('value') if isinstance(content.get(k),dict) else content.get(k)
        venue=value('venue') or ''
        if not venue or 'submitted' in venue.casefold():return None
        return dict(title=value('title') or '',venue=venue,authors=value('authors') or [],type='openreview_venue',doi='')
    return None


class ProgramParser(HTMLParser):
    def __init__(self,mode):
        super().__init__();self.mode=mode;self.scope=mode if mode!='headings' else ''
        self.heading=None;self.anchor=None;self.entries=[]
    def handle_starttag(self,tag,attrs):
        if tag in {'h1','h2','h3','h4'}:self.heading=[]
        if tag=='a':self.anchor=[]
    def handle_data(self,data):
        if self.heading is not None:self.heading.append(data)
        if self.anchor is not None:self.anchor.append(data)
    def handle_endtag(self,tag):
        if tag in {'h1','h2','h3','h4'} and self.heading is not None:
            text=' '.join(self.heading).casefold()
            if self.mode=='headings':
                if 'workshop' in text:self.scope='workshop'
                elif 'conference' in text and ('oral' in text or 'poster' in text or 'papers' in text):self.scope='conference'
                else:self.scope=''
            self.heading=None
        if tag=='a' and self.anchor is not None:
            title=' '.join(self.anchor).strip()
            if self.scope and title:self.entries.append((title,self.scope))
            self.anchor=None


def reference_label(venue):
    t=' '.join(html.unescape(venue).casefold().split()).replace('–','-').replace('—','-')
    if re.search(r'\bworkshop\b|\bshared task\b|\bshared tasks\b',t):return 'outside_main','workshop'
    if re.search(r'\bdemo\b|\bdemonstrations?\b|student research|tutorial|extended abstracts',t):return 'outside_main','auxiliary'
    if re.search(r'\bjournal\b|\btransactions\b|^j\. ',t) or t in {'computational linguistics','machine learning','artificial intelligence','bioinformatics'}:
        return 'outside_main','journal'
    if 'pattern recognition' in t and 'informatics and mobile engineering' in t:return 'CONF_PRIME','conference'
    if 'conference on natural language learning' in t:return 'CONF_CONLL','conference'
    if 'conference on machine learning and applications' in t:return 'CONF_ICMLA','conference'
    if 'conference on machine learning and cybernetics' in t:return 'CONF_ICMLC','conference'
    if 'conference on multimedia retrieval' in t:return 'CONF_ICMR','conference'
    if 'artificial intelligence and interactive digital entertainment' in t:return 'CONF_AIIDE','conference'
    if 'empirical methods in natural language processing' in t and 'very large corpora' in t:return 'CONF_EMNLP_VLC','conference'
    if ('coling' in t and 'acl' in t) or ('international conference on computational linguistics' in t and 'annual meeting' in t):
        return 'CONF_COLING_ACL','conference'
    if ('acl' in t or 'annual meeting' in t) and ('ijcnlp' in t or 'international joint conference on natural language processing' in t):
        return 'CONF_ACL_IJCNLP','conference'
    if 'empirical methods' in t and 'natural language learning' in t:return 'CONF_EMNLP_CONLL','conference'
    if re.search(r'ecml[/ -]pkdd|machine learning and knowledge discovery in databases',t):return 'CONF_ECML_PKDD','conference'
    found={cid for cid,pattern in dict(TITLE_PATTERNS,**ENRICHED_PATTERNS).items() if re.search(pattern,t)}
    if 'SDM' in found:found.discard('ICDM')
    if len(found)==1:
        cid='CONF_'+next(iter(found))
        if 'companion' in t and 'short paper' not in t:return cid,'track_unclear'
        if not re.search(r'conference|proceedings|annual meeting|colloquium|neural information processing systems|short paper',t):
            return cid,'track_unclear'
        return cid,'conference'
    return '', 'unknown'


def source_supports_name(cid,response):
    if not response.get('ok'):return False
    text=html.unescape(re.sub(r'<[^>]+>',' ',response['text'])).casefold()
    text=' '.join(text.split())
    short=cid.removeprefix('CONF_')
    if short=='PRIME':return 'informatics and mobile engineering' in text
    if short=='EMNLP_VLC':return 'very large corpora' in text and 'empirical methods' in text
    if short=='ACL_IJCNLP':return 'international joint conference on natural language processing' in text and 'annual meeting' in text
    if short=='COLING_ACL':return 'coling' in text and 'acl' in text
    if short=='EMNLP_CONLL':return 'empirical methods' in text and 'natural language learning' in text
    return bool(re.search(TITLE_PATTERNS.get(short,r'(?!)'),text))


def sample_papers(rows):
    rng=random.Random(SEED); groups=defaultdict(list)
    for r in rows:
        if r['mapping_status']=='matched':groups[r['conference_id']].append(r)
    selected={}; kinds={}
    for cid in sorted(groups):
        group=sorted(groups[cid],key=lambda r:r['paper_id'])
        for r in rng.sample(group,min(PER_CONFERENCE,len(group))):
            selected[r['paper_id']]=r;kinds[r['paper_id']]='random_per_conference'
    for r in rows:
        if r['mapping_status']=='matched' and any(re.search(r'informatics and mobile|very large corpora|companion|poster sessions|lake,|khandelwa',e['venue_raw'] or '',re.I) for e in r['evidence']):
            if r['paper_id'] not in selected:selected[r['paper_id']]=r;kinds[r['paper_id']]='risk_only'
    return [selected[pid] for pid in sorted(selected)],kinds


def grade_paper(row, urls, cache, raw):
    observations=[]; local_authors={key(a.get('last')) for sid in row['source_ids'] for a in (raw[sid].get('metadata') or {}).get('authors') or [] if a.get('last')}
    for url in urls:
        m=metadata(cache.get(url,{}))
        if not m:continue
        title_match=key(m['title'])==key(row['title'])
        remote={key(a) for a in m['authors'] if a}
        author_match=bool(local_authors & remote) or (m['type']=='openreview_venue' and any(any(a and a in b for b in remote) for a in local_authors))
        authors='matched' if local_authors and remote and author_match else 'mismatched' if local_authors and remote else 'unavailable'
        cid,kind=reference_label(m['venue'])
        observations.append(dict(url=url,doi=doi_key(m['doi']),reference_title=m['title'],reference_venue=m['venue'],reference_id=cid,
            reference_type=kind,title_match=title_match,author_check=authors))
    for url,(cid,mode) in PROGRAMS.items():
        response=cache.get(url,{})
        if not response.get('ok'):continue
        parser=ProgramParser(mode);parser.feed(response['text'])
        scopes={scope for title,scope in parser.entries if key(title)==key(row['title'])}
        for scope in sorted(scopes):
            observations.append(dict(url=url,doi='',reference_title=row['title'],reference_venue='ICLR official accepted '+scope+' program',
                reference_id='outside_main' if scope=='workshop' else cid,reference_type=scope,title_match=True,author_check='unavailable'))
    accepted=[o for o in observations if o['title_match'] and o['author_check']!='mismatched']
    # Same DOI, same publication: publisher's volume title takes precedence over a less
    # specific Crossref container. Do not merge or suppress different publication DOIs.
    publisher_by_doi={o['doi']:o for o in accepted if o['doi'] and o['url'].startswith('https://aclanthology.org/')}
    accepted=[o for o in accepted if not o['doi'] or o['doi'] not in publisher_by_doi or o is publisher_by_doi[o['doi']]]
    known=[o for o in accepted if o['reference_type'] in {'conference','workshop','auxiliary','journal'}]
    labels={o['reference_id'] for o in known}
    if len(labels)>1:status='publication_conflict_review'
    elif known:
        label=next(iter(labels))
        status='reference_agreement' if label==row['conference_id'] else 'outside_main' if label=='outside_main' else 'different_conference'
    elif accepted:status='venue_or_track_unresolved'
    elif observations:status='identity_review'
    else:status='no_reference_available'
    return dict(paper_id=row['paper_id'],baseline_conference_id=row['conference_id'],title=row['title'],
        status=status,reference_ids='; '.join(sorted(labels)),reference_venues=' | '.join(dict.fromkeys(o['reference_venue'] for o in observations)),
        reference_urls='; '.join(o['url'] for o in observations),
        title_checks='; '.join(str(o['title_match']) for o in observations),author_checks='; '.join(o['author_check'] for o in observations),
        human_verified=False,review_mode='automated_primary_metadata_check',observations=observations)


def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def paper_corrections(outcomes,baseline,corrected_module):
    lookup={r['paper_id']:r for r in baseline}
    corrections=[]
    for r in outcomes:
        if r['status'] not in {'outside_main','different_conference','publication_conflict_review'}:continue
        accepted=[o for o in r['observations'] if o['title_match'] and o['author_check']!='mismatched']
        if r['status']=='publication_conflict_review':
            status,cid,kind='unresolved','','unknown'
        elif r['status']=='outside_main':
            kinds={o['reference_type'] for o in accepted if o['reference_id']=='outside_main'}
            if len(kinds)!=1:continue
            status,cid,kind='excluded','',next(iter(kinds))
        else:
            ids={o['reference_id'] for o in accepted if o['reference_type']=='conference'}
            if len(ids)!=1:continue
            cid=next(iter(ids));status,kind='matched','conference'
            if cid not in corrected_module['REGISTRY']:
                status,cid,kind='unresolved','','unknown'
            # If the alias-rule correction already fixes this paper, no per-paper override.
            names=[corrected_module['classify'](e['venue_raw'] or '') for e in lookup[r['paper_id']]['evidence']]
            raw_labels={d['conference_id'] for d in names if d['mapping_status']=='matched'}
            if raw_labels=={cid}:continue
        corrections.append(dict(paper_id=r['paper_id'],mapping_status=status,conference_id=cid,venue_type=kind,
            reason='source_audit_'+r['status'],source_urls='; '.join(dict.fromkeys(o['url'] for o in accepted)),
            review_mode='source_assisted_automated_review',human_verified=False,
            note='Correction supported by the cached primary-source review; not human gold'))
    return corrections


def self_test():
    assert bib_field('booktitle = "Proceedings of the {ACL} and {IJCNLP}"','booktitle')=='Proceedings of the ACL and IJCNLP'
    assert bib_field('booktitle = {Proceedings of {ACL}}','booktitle')=='Proceedings of ACL'
    assert reference_label('Proceedings of the seventh conference on Natural language learning at HLT-NAACL 2003')[0]=='CONF_CONLL'
    assert reference_label('2013 International Conference on Pattern Recognition, Informatics and Mobile Engineering')[0]=='CONF_PRIME'
    assert reference_label('Workshop on Parsing at ACL')[0]=='outside_main'
    assert reference_label('Proceedings of the International Conference on Machine Learning and Applications')[0]=='CONF_ICMLA'
    p=ProgramParser('headings');p.feed('<h3>Conference Oral Presentations</h3><a>A paper</a><h3>Workshop Posters</h3><a>B paper</a>')
    assert p.entries==[('A paper','conference'),('B paper','workshop')]
    return 7


def audit_enrichment(args):
    out=ROOT/'2_mapping_enriched/review'
    if args.check:
        manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
        for name,record in manifest['inputs'].items():
            if sha(Path(record['path']))!=record['sha256']:raise ValueError('Enrichment audit input changed: '+name)
        for name,digest in manifest['outputs'].items():
            if sha(out/name)!=digest:raise ValueError('Enrichment audit output changed: '+name)
        print(json.dumps(dict(enrichment_audit_check='passed',sample=manifest['sample'])));return
    target_path=ROOT/'2_mapping_enriched/output/paper_conference_links.jsonl'
    rows=load(target_path)
    papers_path=PROJECT/'data/processed/papers.jsonl'
    papers={r['paper_id']:r for r in load(papers_path)}
    raw_path=PROJECT/'data/raw/csfcube/abstracts-csfcube-preds.jsonl'
    raw={str(r['paper_id']):r for r in load(raw_path)}
    snapshot_path=ROOT/'2_mapping_enriched/cache/metadata.jsonl'
    snapshot=load(snapshot_path)
    groups=defaultdict(list)
    for r in rows:
        if r['mapping_status']=='matched' and r['baseline_status']!='matched':
            group='added_from_metadata' if r['verification_level']=='metadata_checked' else 'added_from_raw_aliases'
        elif r['baseline_status']=='matched' and r['mapping_status']!='matched':group='removed_or_withheld'
        elif r['baseline_status']==r['mapping_status']=='matched' and r['baseline_conference_id']!=r['conference_id']:group='changed_conference_id'
        elif r['mapping_status']=='matched' and r['verification_level']=='metadata_checked':group='retained_with_metadata'
        else:continue
        groups[group].append(r)
    rng=random.Random(SEED+1);sample=[]
    for group in sorted(groups):
        for r in rng.sample(sorted(groups[group],key=lambda r:r['paper_id']),min(10,len(groups[group]))):
            sample.append(dict(r,title=papers[r['paper_id']]['title'],audit_group=group))
    urls_by_id={}
    for r in sample:
        urls=paper_urls(r,raw,snapshot)
        urls+=['https://api.crossref.org/works/'+urllib.parse.quote(e['doi'],safe='') for e in r['metadata_evidence'] if e.get('doi')]
        urls_by_id[r['paper_id']]=sorted(set(urls))
    cache={r['url']:r for r in load(CACHE)}
    requests=fetch_urls({u for uu in urls_by_id.values() for u in uu},cache) if args.refresh else 0
    outcomes=[]
    for r in sample:
        checked=grade_paper(r,urls_by_id[r['paper_id']],cache,raw)
        status=checked['status']
        if status=='outside_main':
            result='reference_agreement' if r['mapping_status']=='excluded' else 'reference_outside_main_pending' if r['mapping_status']=='unresolved' else 'reference_contradiction'
        elif status=='different_conference':
            result='unresolved_with_reference' if r['mapping_status']=='unresolved' else 'possible_missed_conference' if r['mapping_status']=='excluded' else 'reference_contradiction'
        else:result=status
        checked.update(audit_group=r['audit_group'],target_status=r['mapping_status'],target_conference_id=r['conference_id'],
                       audit_result=result,target_verification_level=r['verification_level'])
        checked.pop('baseline_conference_id',None)
        outcomes.append(checked)
    out.mkdir(exist_ok=True)
    write_csv(out/'sample_review.csv',[{k:v for k,v in r.items() if k!='observations'} for r in outcomes])
    (out/'paper_evidence.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in outcomes),encoding='utf-8')
    counts=Counter(r['audit_result'] for r in outcomes)
    lines=['# Đối chiếu riêng phần mở rộng/enrichment của bản 2','',
        '**Kiểm tra mẫu bằng nguồn metadata, không phải human gold. Không sửa đè output/nhãn bản 2.**','',
        f'Mẫu {len(outcomes)} bài, seed {SEED+1}, tối đa 10 bài ngẫu nhiên mỗi nhóm thay đổi; không phải mẫu ngẫu nhiên đều của toàn corpus.',
        f'Tra theo định danh từ raw/metadata mục tiêu; không dùng nhãn cũ làm đáp án. Lượt lấy URL mới: {requests}. Nguồn nằm trong snapshot chung của bản 3.', '',
        '| Nhóm | Cỡ nhóm | Số kiểm tra |','|---|---:|---:|']
    lines += [f'| {g} | {len(rr)} | {sum(r["audit_group"]==g for r in outcomes)} |' for g,rr in sorted(groups.items())]
    lines += ['', '| Kết quả đối chiếu | Số mẫu |','|---|---:|']+[f'| {k} | {v} |' for k,v in sorted(counts.items())]
    lines += ['', 'reference_agreement là nguồn ủng hộ quyết định mục tiêu; reference_contradiction là nguồn chỉ khác conference hoặc ngoài main. '
        'Các kết quả unresolved/identity/track/no_reference vẫn cần kiểm tra; không tự coi nhãn sai hoặc đúng. '
        'Chưa dùng tỷ lệ này làm precision/recall của toàn bản 2 và chưa đánh giá độc lập bằng người chấm.', '',
        'Bản 2 vẫn là snapshot đối chứng, bao gồm các rule cũ. Các sửa tên của bản 3 chưa được áp ngược vào bản 2. '
        'Khi chốt bản enriched dùng thực nghiệm, phải hợp nhất sửa rule có nguồn và xem lại các ca bất đồng thay vì cộng nhãn cho tăng số lượng.', '']
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    inputs={'target_links':target_path,'raw':raw_path,'papers':papers_path,'metadata_snapshot':snapshot_path,'source_cache':CACHE,'audit_script':Path(__file__).resolve()}
    manifest=dict(review_mode='source_assisted_automated_review',human_gold=False,seed=SEED+1,sample=len(outcomes),
        groups={g:len(rr) for g,rr in groups.items()},outcomes=dict(counts),
        inputs={k:dict(path=str(p),sha256=sha(p)) for k,p in inputs.items()},
        outputs={n:sha(out/n) for n in ['sample_review.csv','paper_evidence.jsonl','report.md']})
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(enrichment_audit_sample=len(outcomes),outcomes=dict(counts),human_gold=False)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true',help='Fetch only missing public source responses; default replay uses cache')
    parser.add_argument('--check',action='store_true',help='Verify audit input/output hashes without writing')
    parser.add_argument('--enriched',action='store_true',help='Audit a separate stratified sample of version-2 changes')
    args=parser.parse_args()
    tests=self_test()
    if args.enriched:
        audit_enrichment(args);return
    if args.check:
        manifest=json.loads((REVIEW/'manifest.json').read_text(encoding='utf-8'))
        for name,record in manifest['inputs'].items():
            if sha(Path(record['path']))!=record['sha256']:raise ValueError('Audit input changed: '+name)
        for name,digest in manifest['outputs'].items():
            if sha(REVIEW/name)!=digest:raise ValueError('Audit output changed: '+name)
        print(json.dumps(dict(audit_check='passed',sample=manifest['sample'],human_gold=False)));return
    rows=load(BASE/'output/paper_conference_links.jsonl')
    papers={r['paper_id']:r for r in load(PROJECT/'data/processed/papers.jsonl')}
    raw={str(r['paper_id']):r for r in load(PROJECT/'data/raw/csfcube/abstracts-csfcube-preds.jsonl')}
    rows=[dict(r,title=papers[r['paper_id']]['title']) for r in rows]
    sampled,kinds=sample_papers(rows)
    old_cache=load(ROOT/'2_mapping_enriched/cache/metadata.jsonl')
    urls_by_paper={r['paper_id']:paper_urls(r,raw,old_cache)+EXACT_PAPER_URLS.get(r['paper_id'],[]) for r in sampled}
    source_urls={u for uu in REFERENCES.values() for u in uu}
    all_urls=source_urls|{u for uu in urls_by_paper.values() for u in uu}
    cache={r['url']:r for r in load(CACHE)} if CACHE.exists() else {}
    requests=fetch_urls(all_urls,cache) if args.refresh else 0
    if not cache:raise ValueError('Initialize source cache with --refresh; no labels were checked')
    REVIEW.mkdir(exist_ok=True)
    outcomes=[]
    for r in sampled:
        outcome=grade_paper(r,urls_by_paper[r['paper_id']],cache,raw)
        outcome['sample_kind']=kinds[r['paper_id']]
        outcomes.append(outcome)
    with (BASE/'venue_mapping.csv').open(encoding='utf-8-sig',newline='') as stream: alias_rows=list(csv.DictReader(stream))
    matched=[r for r in alias_rows if r['mapping_status']=='matched']
    alias_review=[]
    updated=[]
    corrected_module=runpy.run_path(str(HERE/'preprocess_cube.py'))
    for r in alias_rows:
        out=dict(r)
        if r['mapping_status']=='matched':
            corrected=corrected_module['classify'](r['venue_raw'])
            cid=corrected['conference_id']; short=cid.removeprefix('CONF_')
            refs=REFERENCES.get(short,[])
            available=[u for u in refs if source_supports_name(cid,cache.get(u,{}))]
            if not available:
                available=list(dict.fromkeys(o['url'] for result in outcomes for o in result['observations']
                    if o['title_match'] and o['author_check']!='mismatched' and o['reference_id']==cid))
            status='name_reference_available' if available else 'name_reference_pending'
            if cid!=r['conference_id']:status='series_mapping_corrected'
            track='explicit_main_or_short' if re.search(r'main conference|companion.*short papers|poster sessions',r['venue_raw'],re.I) else 'paper_track_not_proven_by_name'
            note='Source-assisted name review; not human gold; paper-level track still needs evidence'
            out.update(corrected)
            if available:
                out.update(review_status='rule_reviewed',note=note+'; sources: '+' '.join(available))
            alias_review.append(dict(venue_raw=r['venue_raw'],before_id=r['conference_id'],after_id=cid,
                papers_with_this_alias=r['canonical_paper_count'],name_review=status,track_review=track,
                primary_sources='; '.join(refs),source_fetch_success=bool(available),human_verified=False,note=note))
        updated.append(out)
    write_csv(HERE/'venue_mapping.csv',updated)
    write_csv(REVIEW/'alias_review.csv',alias_review)
    write_csv(REVIEW/'paper_sample_review.csv',[{k:v for k,v in r.items() if k!='observations'} for r in outcomes])
    corrections=paper_corrections(outcomes,rows,corrected_module)
    write_csv(REVIEW/'paper_review_overrides.csv',corrections)
    (REVIEW/'paper_evidence.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in outcomes),encoding='utf-8')
    counts=Counter(r['status'] for r in outcomes)
    random_counts=Counter(r['status'] for r in outcomes if r['sample_kind']=='random_per_conference')
    by_conf=defaultdict(Counter)
    for r in outcomes:by_conf[r['baseline_conference_id']][r['status']]+=1
    lines=['# Kiểm tra nguồn cho mapping bản 1','',
        '**Đây là kiểm tra tên và đối chiếu mẫu bằng nguồn thư mục, có AI hỗ trợ; chưa phải human gold hoặc review độc lập bởi người chấm.**','',
        f'- Đã xét **{len(matched)} chuỗi venue matched** thuộc **{len(by_conf)} conference IDs** của bản 1; '
        f"**{sum(not r['source_fetch_success'] for r in alias_review)} chuỗi** còn thiếu nguồn tên truy xuất được.",
        f'- Mẫu ngẫu nhiên: tối đa {PER_CONFERENCE} bài/hội nghị, seed {SEED}; **{sum(random_counts.values())} bài**. Thêm **{len(outcomes)-sum(random_counts.values())} ca rủi ro** ngoài mẫu ngẫu nhiên.',
        '- Mẫu rủi ro được thống kê riêng, không trộn để ước lượng độ chính xác.',
        '- Crossref/ACL Anthology được truy vấn theo DOI/ACL ID; DOI gợi ý từ cache S2 chỉ dùng tìm nguồn. Không đọc nhãn kết quả cũ làm đáp án.',
        f'- Snapshot giữ **{len(cache)} phản hồi URL** (gồm lỗi); lượt lấy nguồn mới trong lần ghi báo cáo này: {requests}. Chạy lại không refresh dùng nguyên snapshot.',
        '- Một số nguồn ICLR được tìm bằng web để xác định trang chương trình chính thức; kết luận lấy từ danh sách main/workshop trong trang nguồn, không lấy câu trả lời/tóm tắt của LLM làm nhãn.','',
        '## Kết quả đối chiếu mẫu','', '| Kết quả | Mẫu ngẫu nhiên | Thêm ca rủi ro |','|---|---:|---:|']
    lines += [f'| {s} | {random_counts[s]} | {counts[s]-random_counts[s]} |' for s in sorted(counts)]
    lines += ['', 'Ý nghĩa: reference_agreement = nguồn cùng conference; different_conference = nguồn chỉ conference khác; '
        'outside_main = nguồn chỉ workshop/ấn phẩm ngoài đích; publication_conflict_review = nhiều bản công bố chưa chốt; '
        'identity_review = title/tác giả chưa khớp; venue_or_track_unresolved = chưa rõ venue/track; no_reference_available = chưa lấy được nguồn phù hợp.', '']
    lines += ['', 'reference_agreement chỉ là đồng thuận với metadata đạt điều kiện title/tác giả, không phải precision đã được người chấm đo. '
        'Ngoài main hoặc khác conference là tín hiệu cần sửa nhãn/raw hoặc policy; nguồn thiếu/khác title không tự coi là nhãn sai.', '',
        '## Lỗi quy tắc đã sửa trong bản 3','',
        '- PRIME 2013 có tên kéo dài sau “Pattern Recognition”; quy tắc cũ gán nhầm ICPR. Bản 3 giữ CONF_PRIME riêng, có DOI/publisher metadata làm căn cứ.',
        '- Joint SIGDAT EMNLP/VLC được giữ CONF_EMNLP_VLC riêng để nhất quán chính sách joint, thay vì âm thầm gộp EMNLP.',
        '- Giữ short papers thuộc main khi nguồn chỉ rõ; không tự loại poster sessions thuộc main. Tên conference trần chưa chứng minh từng bài là main.',
        f'- Bản 1 và 2 được giữ nguyên nhãn. Bản 3 sửa rule tên và áp dụng **{len(corrections)} chỉnh sửa từng bài có căn cứ** trong paper_review_overrides.csv; không mở rộng tra nhãn cho toàn corpus.', '',
        '## Theo hội nghị','', '| ID bản 1 | Số kiểm tra | Đồng thuận nguồn | Ngoài main | Khác conference | Còn cần review |','|---|---:|---:|---:|---:|---:|']
    for cid,c in sorted(by_conf.items()):
        lines.append(f"| {cid} | {sum(c.values())} | {c['reference_agreement']} | {c['outside_main']} | {c['different_conference']} | {sum(c.values())-c['reference_agreement']-c['outside_main']-c['different_conference']} |")
    lines+=['', '## Việc còn lại','',
        '- Kiểm tra bằng người chấm/nguồn bài thực tế đối với các ca bất đồng, danh tính hoặc track chưa rõ, đặc biệt các alias quá rộng.',
        '- Chốt tập hội nghị thực nghiệm rồi chọn mẫu kiểm định độc lập lớn hơn nếu muốn công bố precision/recall/độ tin cậy.',
        '- Chưa thể gọi toàn bộ nhãn bản 3 là human_verified. Việc sửa hai rule không giải quyết mọi sai lệch metadata raw.',
        '- Bước này kiểm định bản 1; chưa kiểm định độc lập toàn bộ phần enrichment của bản 2.', '']
    (REVIEW/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    inputs={'baseline_links':BASE/'output/paper_conference_links.jsonl','baseline_mapping':BASE/'venue_mapping.csv',
            'raw':PROJECT/'data/raw/csfcube/abstracts-csfcube-preds.jsonl','papers':PROJECT/'data/processed/papers.jsonl',
            'metadata_snapshot':ROOT/'2_mapping_enriched/cache/metadata.jsonl','audit_script':Path(__file__).resolve(),
            'reviewed_script':HERE/'preprocess_cube.py','reviewed_mapping':HERE/'venue_mapping.csv','source_cache':CACHE}
    manifest=dict(review_version='1.0.0',review_mode='source_assisted_automated_review',human_gold=False,
        seed=SEED,self_tests_passed=tests,cached_source_responses=len(cache),sample=dict(total=len(outcomes),random=sum(random_counts.values()),risk_only=len(outcomes)-sum(random_counts.values()),conferences=len(by_conf)),
        outcomes=dict(counts),random_outcomes=dict(random_counts),aliases=len(matched),
        corrected_aliases=sum(r['before_id']!=r['after_id'] for r in alias_review),paper_corrections=len(corrections),
        inputs={k:dict(path=str(p),sha256=sha(p)) for k,p in inputs.items()},
        outputs={name:sha(REVIEW/name) for name in ['alias_review.csv','paper_sample_review.csv','paper_evidence.jsonl','paper_review_overrides.csv','report.md']})
    (REVIEW/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:manifest[k] for k in ['sample','outcomes','corrected_aliases','human_gold']},ensure_ascii=True,indent=2))


if __name__=='__main__':main()
