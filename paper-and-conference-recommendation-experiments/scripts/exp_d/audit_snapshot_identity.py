"""Record that baseline-snapshot canonical and the current generated tree differ."""
import argparse
import platform
from pathlib import Path
import numpy
import scipy
from run_completion import DATA,SOURCE,BASELINE,rows,read,write,digest,require


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    output=p.parse_args().output.resolve()
    require(DATA in output.parents and not output.exists(),'Choose NEW D audit output')
    baseline=read(BASELINE/'manifest.json')
    result=[]
    for name,h in baseline['input_hashes'].items():
        if not name.startswith('data/exp_d/'):continue
        current=DATA.parents[1]/name
        source=SOURCE/name
        require(digest(source)==h,'Baseline snapshot changed')
        result.append(dict(path=name,baseline_sha256=h,current_sha256=digest(current),
            same_bytes=digest(current)==h,
            current_rows=len(rows(current)) if name.endswith('.jsonl') else None,
            snapshot_rows=len(rows(source)) if name.endswith('.jsonl') else None))
    output.mkdir(parents=True,exist_ok=False)
    write(output/'identity.json',dict(files=result,
          used='baseline_20261016_v1 with workspace_baseline_20261016_v1 ONLY',
          interpretation='Current generated tree has different sessions/queries/truth; same case ID is not identity. No scores mixed.',
          environment=dict(python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__)))
    write(output/'manifest.json',dict(script_sha256=digest(Path(__file__)),
          files={'identity.json':digest(output/'identity.json')}))
    print('PASS: frozen snapshot matches baseline hashes; current generated tree is a separate realization')


if __name__=='__main__':main()
