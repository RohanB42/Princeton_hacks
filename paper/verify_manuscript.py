"""Check the built review PDF and selected source-backed numerical invariants."""
from pathlib import Path
import csv
import hashlib
import json
import re
import sys
PAPER=Path(__file__).resolve().parent
ROOT=PAPER.parent
try:
    import pymupdf as fitz
except ImportError:
    sys.path.insert(0,str(PAPER/'.render-deps'))
    import pymupdf as fitz
PROJECT=PAPER/'AAAI_AI2ASE_Short'
doc=fitz.open(PAPER/'OLIGARCH-anonymous-review.pdf')
texts=[p.get_text() for p in doc]
ref_pages=[i+1 for i,t in enumerate(texts) if re.search(r'(?m)^References$',t)]
assert len(ref_pages)==1,ref_pages
assert ref_pages[0]-1<=8,ref_pages
assert texts[ref_pages[0]-1].lstrip().startswith('References'), 'References must begin on a new page'
assert all(abs(p.rect.width-612)<.1 and abs(p.rect.height-792)<.1 for p in doc)
assert not doc.metadata.get('author')
text='\n'.join(texts)
assert 'Related Work' in text and 'Placeholder:' not in text
assert 'OLIGARCH' in text and 'OligoAL' not in text
assert not re.search(r'\bV[123]\b', text)
source=(PROJECT/'oligarch.tex').read_text()
assert r'\title{OLIGARCH: \underline{OLI}gonucleotide \underline{G}eneration, \underline{A}ctive learning, \underline{R}epresentation Adaptation, and \underline{C}onstrained \underline{H}it Discovery}' in source
for name in ['Rohan','Harrison','Princeton','/Users/','github.com/RohanB42']:
    assert name.lower() not in text.lower(),name
assert '??' not in text
assert 'fig:architecture' not in source and 'figures/architecture' not in source
assert 'Distribution, citation' not in text
assert 'All rights reserved.' in text
fonts={f[0]:f for p in doc for f in p.get_fonts(full=True)}
assert all(f[2]!='Type3' for f in fonts.values())
assert all(doc.extract_font(x)[3] for x in fonts)
log=(PROJECT/'oligarch.log').read_text()
assert not any(x in log for x in ['Overfull','undefined citations','undefined references','LaTeX Error'])
# Recompute headline derived values, without loading hidden biological labels.
with (ROOT/'artifacts/value-of-planning-v1/grid.csv').open() as h: rows=list(csv.DictReader(h))
assert len(rows)==162
assert sum(abs(float(r['optimal'])-float(r['greedy']))<1e-9 for r in rows)==108
assert sum(abs(float(r['optimal'])-float(r['bayesian_rollout']))<1e-9 for r in rows)==150
assert abs(max(float(r['planning_gain']) for r in rows)-.4)<1e-9
means={k:sum(float(r[k]) for r in rows)/len(rows) for k in ['optimal','greedy','bayesian_rollout','random']}
for k,v in {'optimal':1.298591,'greedy':1.260482,'bayesian_rollout':1.296469,'random':.691171}.items():
    assert abs(means[k]-v)<.0000005,(k,means[k])
r=json.loads((ROOT/'artifacts/adaptive-dose-response-v1/report.json').read_text())['roles']['assessment']['methods']
saving=1-r['fixed_early']['mean_measurements']/r['full_grid']['mean_measurements']
assert round(100*saving,1)==63.8
assert all(r[k]['unknown_assertions']==1 for k in ['fixed_early','information_gain','decision_aware'])
a=json.loads((ROOT/'artifacts/molecular-eight-target-extension-v1/eight-target-summary.json').read_text())['summaries']
targets=sorted({x['target'] for x in a});assert len(targets)==8
wins=sum(next(x['mean'] for x in a if x['target']==t and x['method']=='warm_start')>=next(x['mean'] for x in a if x['target']==t and x['method']=='full')-1e-12 for t in targets)
assert wins==6
assert 2880+23188+960==27028
# Numeric tables generated/transcribed into TeX were checked against these originals.
checks={'pdf_pages':len(doc),'references_start_page':ref_pages[0],
'main_text_pages':ref_pages[0]-1,'references_on_separate_page':True,
'main_text_within_eight_pages':True,'letter_size':True,'embedded_fonts':len(fonts),
'font_types':sorted({f[2] for f in fonts.values()}),'type3_fonts':False,
'pdf_author':doc.metadata.get('author'),'unresolved_latex_references':False,
'overflowing_boxes':False,'related_work_completed':True,'requested_title_exact':True,'internal_version_labels_removed':True,
'planning_means_recomputed':means,'planning_cells':len(rows),
'fixed_readout_reduction_percent':100*saving,'pretraining_matches_or_exceeds_targets':wins,
'pdf_sha256':hashlib.sha256((PAPER/'OLIGARCH-anonymous-review.pdf').read_bytes()).hexdigest(),
'visual_review':'Rendered pages inspected separately; not inferred from these automated checks.'}
(PAPER/'verification.json').write_text(json.dumps(checks,indent=2)+'\n')
render=PAPER/'rendered';render.mkdir(exist_ok=True)
for i,p in enumerate(doc):p.get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(render/f'page-{i+1:02}.png')
# Remove only stale page renders from earlier builds made by this script/workflow.
for p in render.glob('page-*.png'):
    if int(p.stem.split('-')[1])>len(doc):p.unlink()
(render/'manuscript-text.txt').write_text(text)
print(json.dumps(checks,indent=2))
