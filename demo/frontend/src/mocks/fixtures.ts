import type {
  AnalysisDetail,
  ConferenceDetail,
  ConferenceExplanationResponse,
  ExampleDetail,
  ModelInfo,
  PaperDetail,
  PaperExplanationResponse,
  PaperRecommendationItem,
  ConferenceRecommendationItem,
  RepresentativePapersResponse,
} from '../types/api';

export const MOCK_MODELS: ModelInfo[] = [
  {
    model_key: 'Qwen3-4B',
    display_name: 'Qwen3-4B-Instruct',
    family: 'Qwen3',
    parameter_size: '4B',
    supported: true,
    precomputed_available: true,
    ranking_artifacts_ready: true,
    unavailable_reason: null,
  },
  {
    model_key: 'Qwen3-8B',
    display_name: 'Qwen3-8B-Instruct',
    family: 'Qwen3',
    parameter_size: '8B',
    supported: true,
    precomputed_available: true,
    ranking_artifacts_ready: true,
    unavailable_reason: null,
  },
  {
    model_key: 'Qwen3-14B',
    display_name: 'Qwen3-14B-Instruct',
    family: 'Qwen3',
    parameter_size: '14B',
    supported: true,
    precomputed_available: true,
    ranking_artifacts_ready: true,
    unavailable_reason: null,
  },
  {
    model_key: 'Llama3.1-8B',
    display_name: 'Llama-3.1-8B-Instruct',
    family: 'Llama 3.1',
    parameter_size: '8B',
    supported: true,
    precomputed_available: true,
    ranking_artifacts_ready: true,
    unavailable_reason: null,
  },
  {
    model_key: 'Gemma2-9B',
    display_name: 'Gemma-2-9B-IT',
    family: 'Gemma 2',
    parameter_size: '9B',
    supported: true,
    precomputed_available: true,
    ranking_artifacts_ready: true,
    unavailable_reason: null,
  },
];

const EX1_TITLE =
  "And That's A Fact: Distinguishing Factual and Emotional Argumentation in Online Dialogue";
const EX1_ABSTRACT =
  'We investigate the characteristics of factual and emotional argumentation styles observed in online debates. Using an annotated set of "factual" and "feeling" debate forum posts, we extract patterns that are highly correlated with factual and emotional arguments, and then apply a bootstrapping methodology to find new patterns in a larger pool of unannotated forum posts. This process automatically produces a large set of patterns representing linguistic expressions that are highly correlated with factual and emotional language. Finally, we analyze the most discriminating patterns to better understand the defining characteristics of factual and emotional arguments.';

const EX2_TITLE =
  'Facet-Aware Scientific Paper and Venue Recommendation via Grounded Concept Extraction';
const EX2_ABSTRACT =
  'Researchers face information overload when searching for relevant literature and selecting suitable publication venues. Traditional keyword or whole-abstract dense retrieval often conflates distinct aspects of a manuscript such as its research problem, methodology, and evaluation datasets. In this work, we propose a five-facet representation framework (problem, task, method, dataset, contribution) extracted by instruction-tuned large language models with verbatim source-grounded evidence. Evaluated on CSFCube and SciFact subsets alongside historical venue profiles, our weighted facet-level scoring improves retrieval interpretability and ranking consistency compared to uniform abstract embeddings.';

export const MOCK_EXAMPLES: ExampleDetail[] = [
  {
    example_id: 'ex_csfcube_argumentation',
    title: EX1_TITLE,
    short_label: 'Argumentation Style Detection (CSFCube P000001)',
    domain: 'Natural Language Processing',
    available_models: ['Qwen3-4B', 'Qwen3-8B', 'Qwen3-14B', 'Llama3.1-8B', 'Gemma2-9B'],
    abstract: EX1_ABSTRACT,
    default_model_key: 'Qwen3-8B',
    precomputed_analyses: {
      'Qwen3-4B': 'analysis_ex1_qwen4b',
      'Qwen3-8B': 'analysis_ex1_qwen8b',
      'Qwen3-14B': 'analysis_ex1_qwen14b',
      'Llama3.1-8B': 'analysis_ex1_llama8b',
      'Gemma2-9B': 'analysis_ex1_gemma9b',
    },
  },
  {
    example_id: 'ex_ds300_facet_rec',
    title: EX2_TITLE,
    short_label: 'Facet-Aware Paper & Venue Recommendation (Demo)',
    domain: 'Information Retrieval / NLP',
    available_models: ['Qwen3-4B', 'Qwen3-8B', 'Llama3.1-8B'],
    abstract: EX2_ABSTRACT,
    default_model_key: 'Qwen3-8B',
    precomputed_analyses: {
      'Qwen3-4B': 'analysis_ex2_qwen8b',
      'Qwen3-8B': 'analysis_ex2_qwen8b',
      'Llama3.1-8B': 'analysis_ex2_qwen8b',
    },
  },
];

function span(
  text: string,
  quote: string,
  source_field: 'title' | 'abstract'
) {
  const idx = text.indexOf(quote);
  if (idx === -1) {
    return { quote, source_field, start_offset: null, end_offset: null, verified: false };
  }
  return {
    quote,
    source_field,
    start_offset: idx,
    end_offset: idx + quote.length,
    verified: true,
  };
}

export const MOCK_ANALYSES: Record<string, AnalysisDetail> = {
  analysis_ex1_qwen8b: {
    analysis_id: 'analysis_ex1_qwen8b',
    title: EX1_TITLE,
    abstract: EX1_ABSTRACT,
    extraction_status: 'completed',
    paper_ranking_status: 'completed',
    conference_ranking_status: 'completed',
    provenance: {
      model_key: 'Qwen3-8B',
      model_display_name: 'Qwen3-8B-Instruct',
      source: 'precomputed',
      prompt_version: 'v3.7-source-first',
      adapter_version: 'ds300-demo-mock-1.0',
      session_id: 'mock-session-01',
      created_at: '2026-11-16T08:30:00Z',
    },
    timings: {
      model_load_ms: null,
      extraction_ms: 1420,
      ranking_ms: 85,
    },
    facets: {
      problem: {
        status: 'ok',
        items: [
          {
            concept: 'distinguishing factual and emotional argumentation styles in online debates',
            evidences: [
              span(
                EX1_ABSTRACT,
                'investigate the characteristics of factual and emotional argumentation styles observed in online debates',
                'abstract'
              ),
            ],
          },
        ],
      },
      task: {
        status: 'ok',
        items: [
          {
            concept: 'argumentation style classification and pattern discovery',
            evidences: [
              span(
                EX1_TITLE,
                'Distinguishing Factual and Emotional Argumentation in Online Dialogue',
                'title'
              ),
              span(
                EX1_ABSTRACT,
                'extract patterns that are highly correlated with factual and emotional arguments',
                'abstract'
              ),
            ],
          },
        ],
      },
      method: {
        status: 'ok',
        items: [
          {
            concept: 'bootstrapping pattern extraction',
            evidences: [
              span(
                EX1_ABSTRACT,
                'apply a bootstrapping methodology to find new patterns in a larger pool of unannotated forum posts',
                'abstract'
              ),
            ],
          },
          {
            concept: 'discriminating linguistic pattern analysis',
            evidences: [
              span(
                EX1_ABSTRACT,
                'analyze the most discriminating patterns to better understand the defining characteristics',
                'abstract'
              ),
            ],
          },
        ],
      },
      dataset: {
        status: 'ok',
        items: [
          {
            concept: 'annotated factual and feeling debate forum posts',
            evidences: [
              span(
                EX1_ABSTRACT,
                'annotated set of "factual" and "feeling" debate forum posts',
                'abstract'
              ),
            ],
          },
          {
            concept: 'unannotated online forum posts pool',
            evidences: [
              span(
                EX1_ABSTRACT,
                'larger pool of unannotated forum posts',
                'abstract'
              ),
            ],
          },
        ],
      },
      contribution: {
        status: 'ok',
        items: [
          {
            concept: 'large set of linguistic expression patterns correlated with factual and emotional language',
            evidences: [
              span(
                EX1_ABSTRACT,
                'automatically produces a large set of patterns representing linguistic expressions that are highly correlated with factual and emotional language',
                'abstract'
              ),
            ],
          },
        ],
      },
    },
  },
  analysis_ex1_qwen4b: {
    analysis_id: 'analysis_ex1_qwen4b',
    title: EX1_TITLE,
    abstract: EX1_ABSTRACT,
    extraction_status: 'completed',
    paper_ranking_status: 'completed',
    conference_ranking_status: 'completed',
    provenance: {
      model_key: 'Qwen3-4B',
      model_display_name: 'Qwen3-4B-Instruct',
      source: 'precomputed',
      prompt_version: 'v3.7-source-first',
      adapter_version: 'ds300-demo-mock-1.0',
      session_id: 'mock-session-01',
      created_at: '2026-11-16T08:31:00Z',
    },
    timings: { model_load_ms: null, extraction_ms: 910, ranking_ms: 82 },
    facets: {
      problem: {
        status: 'ok',
        items: [
          {
            concept: 'factual and emotional argumentation in online debates',
            evidences: [
              span(
                EX1_ABSTRACT,
                'factual and emotional argumentation styles observed in online debates',
                'abstract'
              ),
            ],
          },
        ],
      },
      task: {
        status: 'ok',
        items: [
          {
            concept: 'pattern extraction for argument styles',
            evidences: [
              span(
                EX1_ABSTRACT,
                'extract patterns that are highly correlated with factual and emotional arguments',
                'abstract'
              ),
            ],
          },
        ],
      },
      method: {
        status: 'ok',
        items: [
          {
            concept: 'bootstrapping methodology',
            evidences: [
              span(
                EX1_ABSTRACT,
                'apply a bootstrapping methodology to find new patterns',
                'abstract'
              ),
            ],
          },
        ],
      },
      dataset: {
        status: 'ok',
        items: [
          {
            concept: 'debate forum posts',
            evidences: [
              span(EX1_ABSTRACT, 'debate forum posts', 'abstract'),
            ],
          },
        ],
      },
      contribution: {
        status: 'empty',
        items: [],
      },
    },
  },
  analysis_ex1_qwen14b: {
    analysis_id: 'analysis_ex1_qwen14b',
    title: EX1_TITLE,
    abstract: EX1_ABSTRACT,
    extraction_status: 'completed',
    paper_ranking_status: 'completed',
    conference_ranking_status: 'completed',
    provenance: {
      model_key: 'Qwen3-14B',
      model_display_name: 'Qwen3-14B-Instruct',
      source: 'precomputed',
      prompt_version: 'v3.7-source-first',
      adapter_version: 'ds300-demo-mock-1.0',
      session_id: 'mock-session-01',
      created_at: '2026-11-16T08:32:00Z',
    },
    timings: { model_load_ms: null, extraction_ms: 2150, ranking_ms: 88 },
    facets: {
      problem: {
        status: 'ok',
        items: [
          {
            concept: 'characterizing factual versus emotional argumentation styles in online dialogue',
            evidences: [
              span(
                EX1_ABSTRACT,
                'characteristics of factual and emotional argumentation styles observed in online debates',
                'abstract'
              ),
            ],
          },
        ],
      },
      task: {
        status: 'ok',
        items: [
          {
            concept: 'distinguishing factual and emotional arguments',
            evidences: [
              span(
                EX1_TITLE,
                'Distinguishing Factual and Emotional Argumentation in Online Dialogue',
                'title'
              ),
            ],
          },
          {
            concept: 'correlational linguistic pattern extraction',
            evidences: [
              span(
                EX1_ABSTRACT,
                'extract patterns that are highly correlated with factual and emotional arguments',
                'abstract'
              ),
            ],
          },
        ],
      },
      method: {
        status: 'ok',
        items: [
          {
            concept: 'semi-supervised bootstrapping over unannotated forum posts',
            evidences: [
              span(
                EX1_ABSTRACT,
                'apply a bootstrapping methodology to find new patterns in a larger pool of unannotated forum posts',
                'abstract'
              ),
            ],
          },
          {
            concept: 'discriminating pattern analysis',
            evidences: [
              span(
                EX1_ABSTRACT,
                'analyze the most discriminating patterns to better understand the defining characteristics',
                'abstract'
              ),
            ],
          },
        ],
      },
      dataset: {
        status: 'ok',
        items: [
          {
            concept: 'annotated factual/feeling debate forum posts',
            evidences: [
              span(
                EX1_ABSTRACT,
                'annotated set of "factual" and "feeling" debate forum posts',
                'abstract'
              ),
            ],
          },
          {
            concept: 'unannotated forum posts corpus',
            evidences: [
              span(EX1_ABSTRACT, 'larger pool of unannotated forum posts', 'abstract'),
            ],
          },
        ],
      },
      contribution: {
        status: 'ok',
        items: [
          {
            concept: 'automated discovery of linguistic pattern lexicon for factual/emotional language',
            evidences: [
              span(
                EX1_ABSTRACT,
                'automatically produces a large set of patterns representing linguistic expressions that are highly correlated with factual and emotional language',
                'abstract'
              ),
            ],
          },
        ],
      },
    },
  },
  analysis_ex1_llama8b: {
    analysis_id: 'analysis_ex1_llama8b',
    title: EX1_TITLE,
    abstract: EX1_ABSTRACT,
    extraction_status: 'completed',
    paper_ranking_status: 'completed',
    conference_ranking_status: 'completed',
    provenance: {
      model_key: 'Llama3.1-8B',
      model_display_name: 'Llama-3.1-8B-Instruct',
      source: 'precomputed',
      prompt_version: 'v3.7-source-first',
      adapter_version: 'ds300-demo-mock-1.0',
      session_id: 'mock-session-01',
      created_at: '2026-11-16T08:33:00Z',
    },
    timings: { model_load_ms: null, extraction_ms: 1580, ranking_ms: 85 },
    facets: {
      problem: {
        status: 'ok',
        items: [
          {
            concept: 'identifying factual vs emotional argumentation in online debates',
            evidences: [
              span(
                EX1_ABSTRACT,
                'characteristics of factual and emotional argumentation styles observed in online debates',
                'abstract'
              ),
            ],
          },
        ],
      },
      task: {
        status: 'ok',
        items: [
          {
            concept: 'pattern extraction from debate posts',
            evidences: [
              span(
                EX1_ABSTRACT,
                'extract patterns that are highly correlated with factual and emotional arguments',
                'abstract'
              ),
            ],
          },
        ],
      },
      method: {
        status: 'ok',
        items: [
          {
            concept: 'bootstrapping pattern discovery',
            evidences: [
              span(
                EX1_ABSTRACT,
                'apply a bootstrapping methodology to find new patterns',
                'abstract'
              ),
            ],
          },
        ],
      },
      dataset: {
        status: 'ok',
        items: [
          {
            concept: 'annotated "factual" and "feeling" debate forum posts',
            evidences: [
              span(
                EX1_ABSTRACT,
                'annotated set of "factual" and "feeling" debate forum posts',
                'abstract'
              ),
            ],
          },
        ],
      },
      contribution: {
        status: 'ok',
        items: [
          {
            concept: 'analysis of discriminating linguistic patterns',
            evidences: [
              span(
                EX1_ABSTRACT,
                'analyze the most discriminating patterns to better understand the defining characteristics of factual and emotional arguments',
                'abstract'
              ),
            ],
          },
        ],
      },
    },
  },
  analysis_ex1_gemma9b: {
    analysis_id: 'analysis_ex1_gemma9b',
    title: EX1_TITLE,
    abstract: EX1_ABSTRACT,
    extraction_status: 'completed',
    paper_ranking_status: 'completed',
    conference_ranking_status: 'completed',
    provenance: {
      model_key: 'Gemma2-9B',
      model_display_name: 'Gemma-2-9B-IT',
      source: 'precomputed',
      prompt_version: 'v3.7-source-first',
      adapter_version: 'ds300-demo-mock-1.0',
      session_id: 'mock-session-01',
      created_at: '2026-11-16T08:34:00Z',
    },
    timings: { model_load_ms: null, extraction_ms: 1730, ranking_ms: 85 },
    facets: {
      problem: {
        status: 'ok',
        items: [
          {
            concept: 'distinguishing factual and emotional argumentation styles',
            evidences: [
              span(
                EX1_TITLE,
                'Distinguishing Factual and Emotional Argumentation in Online Dialogue',
                'title'
              ),
            ],
          },
        ],
      },
      task: {
        status: 'ok',
        items: [
          {
            concept: 'discovering correlated linguistic patterns',
            evidences: [
              span(
                EX1_ABSTRACT,
                'find new patterns in a larger pool of unannotated forum posts',
                'abstract'
              ),
            ],
          },
        ],
      },
      method: {
        status: 'ok',
        items: [
          {
            concept: 'bootstrapping methodology',
            evidences: [
              span(EX1_ABSTRACT, 'bootstrapping methodology', 'abstract'),
            ],
          },
        ],
      },
      dataset: {
        status: 'ok',
        items: [
          {
            concept: 'debate forum posts',
            evidences: [
              span(EX1_ABSTRACT, 'debate forum posts', 'abstract'),
            ],
          },
        ],
      },
      contribution: {
        status: 'ok',
        items: [
          {
            concept: 'large set of linguistic expression patterns',
            evidences: [
              span(
                EX1_ABSTRACT,
                'large set of patterns representing linguistic expressions that are highly correlated with factual and emotional language',
                'abstract'
              ),
            ],
          },
        ],
      },
    },
  },
  analysis_ex2_qwen8b: {
    analysis_id: 'analysis_ex2_qwen8b',
    title: EX2_TITLE,
    abstract: EX2_ABSTRACT,
    extraction_status: 'completed',
    paper_ranking_status: 'completed',
    conference_ranking_status: 'completed',
    provenance: {
      model_key: 'Qwen3-8B',
      model_display_name: 'Qwen3-8B-Instruct',
      source: 'precomputed',
      prompt_version: 'v3.7-source-first',
      adapter_version: 'ds300-demo-mock-1.0',
      session_id: 'mock-session-01',
      created_at: '2026-11-16T08:40:00Z',
    },
    timings: { model_load_ms: null, extraction_ms: 1510, ranking_ms: 94 },
    facets: {
      problem: {
        status: 'ok',
        items: [
          {
            concept: 'information overload in literature search and venue selection',
            evidences: [
              span(
                EX2_ABSTRACT,
                'information overload when searching for relevant literature and selecting suitable publication venues',
                'abstract'
              ),
            ],
          },
          {
            concept: 'conflation of distinct manuscript aspects in whole-abstract retrieval',
            evidences: [
              span(
                EX2_ABSTRACT,
                'whole-abstract dense retrieval often conflates distinct aspects of a manuscript',
                'abstract'
              ),
            ],
          },
        ],
      },
      task: {
        status: 'ok',
        items: [
          {
            concept: 'scientific paper and venue recommendation',
            evidences: [
              span(EX2_TITLE, 'Scientific Paper and Venue Recommendation', 'title'),
            ],
          },
        ],
      },
      method: {
        status: 'ok',
        items: [
          {
            concept: 'five-facet representation via instruction-tuned LLMs with source-grounded evidence',
            evidences: [
              span(
                EX2_ABSTRACT,
                'five-facet representation framework (problem, task, method, dataset, contribution) extracted by instruction-tuned large language models with verbatim source-grounded evidence',
                'abstract'
              ),
            ],
          },
          {
            concept: 'weighted facet-level scoring',
            evidences: [
              span(EX2_ABSTRACT, 'weighted facet-level scoring', 'abstract'),
            ],
          },
        ],
      },
      dataset: {
        status: 'ok',
        items: [
          {
            concept: 'CSFCube and SciFact subsets',
            evidences: [
              span(EX2_ABSTRACT, 'CSFCube and SciFact subsets', 'abstract'),
            ],
          },
          {
            concept: 'historical venue profiles',
            evidences: [
              span(EX2_ABSTRACT, 'historical venue profiles', 'abstract'),
            ],
          },
        ],
      },
      contribution: {
        status: 'ok',
        items: [
          {
            concept: 'improved retrieval interpretability and ranking consistency',
            evidences: [
              span(
                EX2_ABSTRACT,
                'improves retrieval interpretability and ranking consistency compared to uniform abstract embeddings',
                'abstract'
              ),
            ],
          },
        ],
      },
    },
  },
};

export const MOCK_PAPERS: Record<string, PaperDetail> = {
  P001181: {
    paper_id: 'P001181',
    title: 'Recognizing Stance and Argumentation Styles in Online Persuasive Forums',
    abstract:
      'Online discussion forums host rich persuasive interactions where participants alternate between evidence-based claims and affective appeals. We construct an annotated corpus of persuasive forum threads and propose a weakly supervised bootstrapping classifier to detect factual versus emotional argumentation cues. Experimental results demonstrate substantial improvements over bag-of-words baselines.',
    authors: ['L. Chen', 'M. Walker', 'R. Anand'],
    year: 2019,
    venue: 'ACL',
    doi: '10.18653/v1/P19-1042',
    url: 'https://aclanthology.org/P19-1042/',
    source: 'csfcube',
    in_corpus: true,
  },
  P001211: {
    paper_id: 'P001211',
    title: 'Bootstrapping Subjectivity and Factuality Lexicons from Debate Threads',
    abstract:
      'Identifying subjective versus factual expressions in user-generated text remains challenging due to domain-specific phrasing. We introduce a bootstrapping algorithm seeded with high-precision debate phrases to expand lexicons over large unannotated forum archives, improving downstream argument mining.',
    authors: ['S. Oraby', 'P. Reed', 'J. Abbott'],
    year: 2017,
    venue: 'EMNLP',
    doi: '10.18653/v1/D17-1120',
    url: 'https://aclanthology.org/D17-1120/',
    source: 'csfcube',
    in_corpus: true,
  },
  P001506: {
    paper_id: 'P001506',
    title: 'Faceted Scientific Document Retrieval Using Structured Aspect Representations',
    abstract:
      'Scientific papers encode multiple semantic facets including problem statements, methods, and evaluation datasets. We evaluate facet-specific TF-IDF and dense encoders on CSFCube, showing that decomposing abstracts into structured facets yields higher ranking accuracy and transparent explanations.',
    authors: ['S. Mysore', 'A. McCallum', 'H. Zamani'],
    year: 2021,
    venue: 'SIGIR',
    doi: '10.1145/3404835.3462912',
    url: 'https://dl.acm.org/doi/10.1145/3404835.3462912',
    source: 'csfcube',
    in_corpus: true,
  },
  P001604: {
    paper_id: 'P001604',
    title: 'Linguistic Markers of Emotional Appeals in Social Media Debates',
    abstract:
      'We study how emotional and moral framing shapes persuasion in online debates. Using annotated debate posts, we extract n-gram and syntactic markers that differentiate emotional appeals from factual citations.',
    authors: ['K. Habernal', 'I. Gurevych'],
    year: 2018,
    venue: 'NAACL',
    doi: '10.18653/v1/N18-1055',
    url: 'https://aclanthology.org/N18-1055/',
    source: 'csfcube',
    in_corpus: true,
  },
  P002380: {
    paper_id: 'P002380',
    title: 'Venue Recommendation for Academic Manuscripts via Historical Topic Profiles',
    abstract:
      'Selecting an appropriate conference venue requires matching a manuscript against historical publication profiles. We model each conference using facet-weighted centroids built from past accepted papers and evaluate top-k venue ranking across NLP and IR conferences.',
    authors: ['T. Nguyen', 'H. Le', 'D. Tran'],
    year: 2023,
    venue: 'CIKM',
    doi: '10.1145/3583780.3615011',
    url: 'https://dl.acm.org/doi/10.1145/3583780.3615011',
    source: 'scifact',
    in_corpus: true,
  },
};

export const MOCK_PAPER_RANKINGS: PaperRecommendationItem[] = [
  {
    rank: 1,
    paper_id: 'P001211',
    title: MOCK_PAPERS.P001211.title,
    authors: MOCK_PAPERS.P001211.authors,
    year: 2017,
    venue: 'EMNLP',
    total_score: 0.482,
    score_unit: 'weighted_facet_cosine (0–1)',
    supporting_facets: ['method', 'dataset', 'problem'],
  },
  {
    rank: 2,
    paper_id: 'P001181',
    title: MOCK_PAPERS.P001181.title,
    authors: MOCK_PAPERS.P001181.authors,
    year: 2019,
    venue: 'ACL',
    total_score: 0.431,
    score_unit: 'weighted_facet_cosine (0–1)',
    supporting_facets: ['problem', 'task', 'method'],
  },
  {
    rank: 3,
    paper_id: 'P001604',
    title: MOCK_PAPERS.P001604.title,
    authors: MOCK_PAPERS.P001604.authors,
    year: 2018,
    venue: 'NAACL',
    total_score: 0.367,
    score_unit: 'weighted_facet_cosine (0–1)',
    supporting_facets: ['problem', 'dataset', 'contribution'],
  },
  {
    rank: 4,
    paper_id: 'P001506',
    title: MOCK_PAPERS.P001506.title,
    authors: MOCK_PAPERS.P001506.authors,
    year: 2021,
    venue: 'SIGIR',
    total_score: 0.214,
    score_unit: 'weighted_facet_cosine (0–1)',
    supporting_facets: ['task', 'method'],
  },
  {
    rank: 5,
    paper_id: 'P002380',
    title: MOCK_PAPERS.P002380.title,
    authors: MOCK_PAPERS.P002380.authors,
    year: 2023,
    venue: 'CIKM',
    total_score: 0.148,
    score_unit: 'weighted_facet_cosine (0–1)',
    supporting_facets: ['method'],
  },
];

export const MOCK_CONFERENCES: Record<string, ConferenceDetail> = {
  conf_acl: {
    conference_id: 'conf_acl',
    name: 'Annual Meeting of the Association for Computational Linguistics',
    acronym: 'ACL',
    url: 'https://aclanthology.org/venues/acl/',
    topic_profile_description:
      'Hồ sơ chủ đề được xây dựng từ tập các bài báo lịch sử thuộc nhánh Computational Linguistics & Natural Language Processing (argument mining, discourse analysis, LLM information extraction).',
    profile_built_from: 'Hồ sơ tổng hợp từ 142 bài báo lịch sử trong corpus DS300',
    historical_paper_count: 142,
    year_range: '2015–2024',
    cutoff_note: 'Dữ liệu hồ sơ tính đến cutoff 2024; không bao gồm thông tin deadline/call-for-papers tương lai.',
    coverage_note: 'Độ phủ facet đạt 96.5% trên tập bài lịch sử.',
    sparse_profile_warning: null,
  },
  conf_emnlp: {
    conference_id: 'conf_emnlp',
    name: 'Conference on Empirical Methods in Natural Language Processing',
    acronym: 'EMNLP',
    url: 'https://aclanthology.org/venues/emnlp/',
    topic_profile_description:
      'Hồ sơ chủ đề tập trung vào các phương pháp thực nghiệm NLP, bootstrapping/weak supervision, phân tích ngôn ngữ tranh luận và trích xuất thông tin có kiểm chứng.',
    profile_built_from: 'Hồ sơ tổng hợp từ 118 bài báo lịch sử trong corpus DS300',
    historical_paper_count: 118,
    year_range: '2016–2024',
    cutoff_note: 'Dữ liệu hồ sơ tính đến cutoff 2024.',
    coverage_note: 'Độ phủ facet đạt 94.9% trên tập bài lịch sử.',
    sparse_profile_warning: null,
  },
  conf_sigir: {
    conference_id: 'conf_sigir',
    name: 'International ACM SIGIR Conference on Research and Development in Information Retrieval',
    acronym: 'SIGIR',
    url: 'https://sigir.org/',
    topic_profile_description:
      'Hồ sơ chủ đề về truy xuất thông tin, xếp hạng tài liệu khoa học theo facet và hệ thống gợi ý có giải thích.',
    profile_built_from: 'Hồ sơ tổng hợp từ 47 bài báo lịch sử trong corpus DS300',
    historical_paper_count: 47,
    year_range: '2018–2024',
    cutoff_note: 'Dữ liệu hồ sơ tính đến cutoff 2024.',
    coverage_note: 'Độ phủ facet đạt 91.5%.',
    sparse_profile_warning:
      'Số lượng bài lịch sử trong tập hội nghị này ở mức trung bình (47 bài); điểm khớp chủ đề mang tính tham khảo theo dữ liệu hiện có.',
  },
};

export const MOCK_CONFERENCE_RANKINGS: ConferenceRecommendationItem[] = [
  {
    rank: 1,
    conference_id: 'conf_acl',
    name: MOCK_CONFERENCES.conf_acl.name,
    acronym: 'ACL',
    match_score: 0.461,
    score_unit: 'weighted_facet_centroid_cosine (0–1)',
    prominent_facets: ['problem', 'task', 'method'],
    historical_paper_count: 142,
  },
  {
    rank: 2,
    conference_id: 'conf_emnlp',
    name: MOCK_CONFERENCES.conf_emnlp.name,
    acronym: 'EMNLP',
    match_score: 0.439,
    score_unit: 'weighted_facet_centroid_cosine (0–1)',
    prominent_facets: ['method', 'dataset', 'contribution'],
    historical_paper_count: 118,
  },
  {
    rank: 3,
    conference_id: 'conf_sigir',
    name: MOCK_CONFERENCES.conf_sigir.name,
    acronym: 'SIGIR',
    match_score: 0.245,
    score_unit: 'weighted_facet_centroid_cosine (0–1)',
    prominent_facets: ['task', 'method'],
    historical_paper_count: 47,
  },
];

export function buildMockPaperExplanation(
  analysisId: string,
  paperId: string
): PaperExplanationResponse {
  const analysis = MOCK_ANALYSES[analysisId] || MOCK_ANALYSES.analysis_ex1_qwen8b;
  const paper = MOCK_PAPERS[paperId] || MOCK_PAPERS.P001211;
  const recItem = MOCK_PAPER_RANKINGS.find((p) => p.paper_id === paperId);
  const totalScore = recItem?.total_score ?? 0.42;

  return {
    analysis_id: analysis.analysis_id,
    paper_id: paper.paper_id,
    total_score: totalScore,
    score_unit: 'weighted_facet_cosine (0–1)',
    scorer_name: 'exp_b_weighted_facets_tfidf',
    formula_description:
      'Tổng có trọng số độ tương đồng TF-IDF cosine theo từng facet: sum(w_f * cosine(q_f, p_f)). Trọng số cố định theo cấu hình thực nghiệm B.',
    summary_explanation: `Bài báo "${paper.title}" đạt điểm tổng ${totalScore.toFixed(3)} (thang weighted_facet_cosine 0–1) nhờ sự trùng khớp mạnh ở các facet Phương pháp (bootstrapping / pattern extraction), Vấn đề (argumentation style) và Dữ liệu (debate forum posts).`,
    facet_breakdowns: [
      {
        facet: 'problem',
        query_concepts: analysis.facets.problem.items,
        target_concepts: [
          {
            concept: 'identifying subjective versus factual expressions in debate threads',
            evidences: [
              span(
                paper.abstract,
                'Identifying subjective versus factual expressions in user-generated text remains challenging',
                'abstract'
              ),
            ],
          },
        ],
        query_status: analysis.facets.problem.status,
        target_status: 'ok',
        similarity_score: 0.51,
        weight: 0.25,
        contribution_score: 0.1275,
        note: 'Khớp cao về bài toán phân biệt lập luận thực tế và cảm tính.',
      },
      {
        facet: 'task',
        query_concepts: analysis.facets.task.items,
        target_concepts: [
          {
            concept: 'lexicon expansion and argument cue detection',
            evidences: [
              span(paper.title, paper.title, 'title'),
            ],
          },
        ],
        query_status: analysis.facets.task.status,
        target_status: 'ok',
        similarity_score: 0.44,
        weight: 0.2,
        contribution_score: 0.088,
        note: null,
      },
      {
        facet: 'method',
        query_concepts: analysis.facets.method.items,
        target_concepts: [
          {
            concept: 'weakly supervised bootstrapping algorithm',
            evidences: [
              span(
                paper.abstract,
                'bootstrapping',
                'abstract'
              ),
            ],
          },
        ],
        query_status: analysis.facets.method.status,
        target_status: 'ok',
        similarity_score: 0.62,
        weight: 0.25,
        contribution_score: 0.155,
        note: 'Cùng sử dụng kỹ thuật bootstrapping trên tập forum chưa gán nhãn.',
      },
      {
        facet: 'dataset',
        query_concepts: analysis.facets.dataset.items,
        target_concepts: [
          {
            concept: 'unannotated forum archives and debate threads',
            evidences: [
              span(paper.abstract, 'forum', 'abstract'),
            ],
          },
        ],
        query_status: analysis.facets.dataset.status,
        target_status: 'ok',
        similarity_score: 0.49,
        weight: 0.15,
        contribution_score: 0.0735,
        note: null,
      },
      {
        facet: 'contribution',
        query_concepts: analysis.facets.contribution.items,
        target_concepts: [],
        query_status: analysis.facets.contribution.status,
        target_status: 'empty',
        similarity_score: 0.0,
        weight: 0.15,
        contribution_score: 0.0,
        note: 'Bài báo đích không ghi nhận concept contribution rõ ràng trong bản trích xuất.',
      },
    ],
  };
}

export function buildMockConferenceExplanation(
  analysisId: string,
  conferenceId: string
): ConferenceExplanationResponse {
  const analysis = MOCK_ANALYSES[analysisId] || MOCK_ANALYSES.analysis_ex1_qwen8b;
  const conf = MOCK_CONFERENCES[conferenceId] || MOCK_CONFERENCES.conf_acl;
  const rankItem = MOCK_CONFERENCE_RANKINGS.find((c) => c.conference_id === conferenceId);
  const matchScore = rankItem?.match_score ?? 0.44;

  return {
    analysis_id: analysis.analysis_id,
    conference_id: conf.conference_id,
    match_score: matchScore,
    score_unit: 'weighted_facet_centroid_cosine (0–1)',
    scorer_name: 'venue_weighted_centroid_tfidf',
    formula_description:
      'Đo cosine giữa vector từng facet của manuscript với vector tâm (centroid) của các bài báo lịch sử thuộc hội nghị, sau đó tính tổng có trọng số.',
    disclaimer:
      'Điểm số biểu diễn mức độ tương đồng nội dung với hồ sơ bài lịch sử của hội nghị, KHÔNG phải xác suất bài báo được chấp nhận (acceptance rate).',
    summary_explanation: `Manuscript khớp tốt với hồ sơ chủ đề của ${conf.acronym} (${matchScore.toFixed(3)}) do sự tương đồng ở các nhánh Problem (argumentation analysis), Task (linguistic pattern detection) và Method (bootstrapping).`,
    sparse_profile_warning: conf.sparse_profile_warning,
    facet_scores: [
      {
        facet: 'problem',
        query_concepts: analysis.facets.problem.items,
        profile_keywords: ['argumentation', 'online debate', 'discourse', 'stance detection'],
        similarity_score: 0.54,
        weight: 0.25,
        contribution_score: 0.135,
      },
      {
        facet: 'task',
        query_concepts: analysis.facets.task.items,
        profile_keywords: ['argument classification', 'pattern extraction', 'opinion mining'],
        similarity_score: 0.48,
        weight: 0.2,
        contribution_score: 0.096,
      },
      {
        facet: 'method',
        query_concepts: analysis.facets.method.items,
        profile_keywords: ['bootstrapping', 'semi-supervised', 'linguistic patterns'],
        similarity_score: 0.51,
        weight: 0.25,
        contribution_score: 0.1275,
      },
      {
        facet: 'dataset',
        query_concepts: analysis.facets.dataset.items,
        profile_keywords: ['debate forum', 'annotated corpus', 'dialogue threads'],
        similarity_score: 0.36,
        weight: 0.15,
        contribution_score: 0.054,
      },
      {
        facet: 'contribution',
        query_concepts: analysis.facets.contribution.items,
        profile_keywords: ['lexicon resource', 'empirical analysis'],
        similarity_score: 0.32,
        weight: 0.15,
        contribution_score: 0.048,
      },
    ],
  };
}

export function buildMockRepresentativePapers(
  analysisId: string,
  conferenceId: string,
  limit = 5
): RepresentativePapersResponse {
  const conf = MOCK_CONFERENCES[conferenceId] || MOCK_CONFERENCES.conf_acl;
  const candidates = Object.values(MOCK_PAPERS).filter(
    (p) => p.venue?.toLowerCase() === conf.acronym.toLowerCase() || conf.acronym === 'ACL'
  );

  return {
    analysis_id: analysisId,
    conference_id: conf.conference_id,
    selection_rule: 'top_nearest_to_query_in_venue_profile',
    note: 'Các bài báo lịch sử dưới đây được chọn theo độ gần với manuscript để minh họa cho hồ sơ chủ đề hội nghị (không phải toàn bộ cơ sở tính điểm centroid).',
    items: candidates.slice(0, limit).map((p) => ({
      paper_id: p.paper_id,
      in_corpus: p.in_corpus,
      title: p.title,
      year: p.year,
      authors: p.authors,
      url: p.url,
      abstract: p.abstract,
      supporting_facets: ['problem', 'method'],
      evidences: [
        {
          quote: p.abstract.slice(0, 140) + '...',
          source_field: 'abstract',
          start_offset: 0,
          end_offset: 140,
          verified: true,
        },
      ],
      selection_rule: 'nearest_query_neighbor',
    })),
  };
}
