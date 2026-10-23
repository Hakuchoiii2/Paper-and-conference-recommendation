def main():
    import base64
    code_bundle = Path('/tmp/v2_test_code.zip')
    code_bundle.write_bytes(base64.b64decode(CODE_B64))
    extract_bundle(code_bundle,PROJECT,BUNDLE_SHA256)
    settings = json.loads((PROJECT/'v2_settings.json').read_text(encoding='utf-8'))
    bundles = list(Path('/kaggle/input').rglob('qlora_bundle.zip.bin'))
    if len(bundles) != 1:
        raise ValueError('Missing or ambiguous existing private v1 input bundle')
    if hashlib.sha256(bundles[0].read_bytes()).hexdigest() != settings['source_bundle_sha256']:
        raise ValueError('Existing private test bundle differs from the frozen release')
    if set(settings['test_files']) != {'model_inputs/test_papers.jsonl','evaluation_only/test_references.jsonl'}:
        raise ValueError('Unexpected test input names')
    with zipfile.ZipFile(bundles[0]) as archive:
        for name,expected in {**settings['test_files'],**settings['embedding_files']}.items():
            content = archive.read(name)
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError('Existing sealed test file differs')
            target = PROJECT/name
            if not target.resolve().is_relative_to(PROJECT.resolve()):
                raise ValueError('Unsafe existing input path')
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(content)
    candidates = [path.parent for path in Path('/kaggle/input').rglob('training_metadata.json')
                  if path.parent.name == 'qwen3-8b-facets-qlora-v2'
                  and hashlib.sha256(path.read_bytes()).hexdigest() == settings['adapter_metadata_sha256']]
    if len(candidates) != 1:
        raise ValueError('Missing or ambiguous dev-selected v2 adapter from the attached training kernel')
    os.environ.update(HF_HOME='/tmp/exp_a_huggingface',TOKENIZERS_PARALLELISM='false',
                      PYTHONDONTWRITEBYTECODE='1',USE_TF='0')
    subprocess.run([sys.executable,'-m','pip','install','--quiet','transformers==4.57.6',
        'accelerate==1.15.0','bitsandbytes==0.50.2','peft==0.18.1'],check=True)
    sys.path.insert(0,str(PROJECT/'data/exp_a/finetuning/v2'))
    import evaluation
    evaluation.run(PROJECT,settings,candidates[0])


if __name__ == '__main__':
    main()
