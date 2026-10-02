# IT corpus bootstrap plan

Approved scope: preserve both official raw datasets, merge only IT-related papers,
create the agreed data-first layout. Python standard library only.

1. Download CSFCube v1.1 and official SciFact; preserve native labels and splits.
2. Test conservative scope filtering, normalization, stable IDs and deduplication.
3. Implement source downloader, corpus builder, real fixture builder and validator.
4. Keep a scope audit and versioned human overrides. Use CSFCube's documented CS
   sampling scope; require explicit computing-method evidence for SciFact.
5. Merge by shared identifiers, then normalized title with compatible abstracts;
   flag conflicting titles and preserve all source references. Reuse existing IDs.
6. Generate a deterministic 50-paper real sample without invented facets or gold.
7. Document contract, schemas, facet guideline and seven-section A-E READMEs.
8. Validate corruptions, counts, checksums and byte-identical rebuilds. Move the
   verified project to DS300/Đồ án without overwriting any existing project.

Scope filtering is provisional and requires audit review before a real freeze.
Do not implement models, create gold, reinterpret native labels/splits, fabricate
conference judgments, or push to GitHub. The original DS300 plan is not available.
