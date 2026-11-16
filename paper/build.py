"""Compile the anonymous manuscript with the unchanged AAAI-27 kit."""
from pathlib import Path
import shutil
import subprocess
import sys
PAPER=Path(__file__).resolve().parent
PROJECT=PAPER/'AAAI_AI2ASE_Short'
LOCAL=PAPER/'.tex-runtime/TinyTeX/bin/universal-darwin'
def binary(name):
    found=shutil.which(name)
    if found: return found
    p=LOCAL/name
    if p.exists(): return str(p)
    raise SystemExit(f'{name} is required. Install a standard TeX Live distribution.')
for name,args in [('pdflatex',['-interaction=nonstopmode','-halt-on-error','oligarch.tex']),
                  ('bibtex',['oligarch']),
                  ('pdflatex',['-interaction=nonstopmode','-halt-on-error','oligarch.tex']),
                  ('pdflatex',['-interaction=nonstopmode','-halt-on-error','oligarch.tex'])]:
    result=subprocess.run([binary(name),*args],cwd=PROJECT,capture_output=True,text=True)
    (PROJECT/f'build-{name}.txt').write_text(result.stdout+result.stderr)
    if result.returncode:
        print(result.stdout[-4000:]+result.stderr);sys.exit(result.returncode)
log=(PROJECT/'oligarch.log').read_text()
for line in log.splitlines():
    if any(s in line for s in ['Warning:','Overfull','Output written']):print(line)
shutil.copy2(PROJECT/'oligarch.pdf',PAPER/'OLIGARCH-anonymous-review.pdf')
print('Built paper/OLIGARCH-anonymous-review.pdf')
