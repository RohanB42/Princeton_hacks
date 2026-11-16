"""Package the current anonymous LaTeX sources without internal evidence files."""
from pathlib import Path
import zipfile
P=Path(__file__).resolve().parent
D=P/'AAAI_AI2ASE_Short'
with zipfile.ZipFile(P/'OLIGARCH-latex-source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for n in ['oligarch.tex','references.bib','aaai2027.sty','aaai2027.bst']:
  z.write(D/n,n)
 for n in ['prediction','measurement_planning','molecular']:
  z.write(D/'figures'/f'{n}.pdf',f'figures/{n}.pdf')
 z.writestr('README.txt','OLIGARCH anonymous review manuscript\n\nCompile with pdfLaTeX (not XeLaTeX or LuaLaTeX):\n  pdflatex -interaction=nonstopmode -halt-on-error oligarch.tex\n  bibtex oligarch\n  pdflatex -interaction=nonstopmode -halt-on-error oligarch.tex\n  pdflatex -interaction=nonstopmode -halt-on-error oligarch.tex\n\nRequires a standard TeX Live installation with the supplied AAAI-27 style dependencies.\nThe style automatically selects aaai2027.bst. Includes the Related Work section.\nReferences start on a new page in this review draft; remove the explicit break for camera-ready.\nNo private paths, raw assay data or model weights are included.\n')
print('Created paper/OLIGARCH-latex-source.zip')
