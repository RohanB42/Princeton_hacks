"""Rebuild manuscript figures from frozen reports; no experiments or fitting.
Run with Python + numpy/matplotlib from the repository root.
"""
import csv
import hashlib
import json
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'paper'
os.environ['MPLCONFIGDIR'] = str(PAPER / '.mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
OUT = PAPER / 'AAAI_AI2ASE_Short' / 'figures'
OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':9, 'axes.titlesize':10,
 'axes.labelsize':9, 'xtick.labelsize':8, 'ytick.labelsize':8, 'pdf.fonttype':42,
 'ps.fonttype':42, 'axes.spines.top':False, 'axes.spines.right':False})
COL = {'full':'#C85A23', 'warm_start':'#197D78', 'random':'#8A9299', 'greedy':'#4B58A6'}
used=[]
def read_json(path):
 p=ROOT/path; used.append(p); return json.loads(p.read_text())
def save(fig,name):
 fig.savefig(OUT/(name+'.pdf'), bbox_inches='tight', pad_inches=.04,
             metadata={'Creator':'OLIGARCH figure generator','Author':''})
 fig.savefig(OUT/(name+'.png'),dpi=200,bbox_inches='tight',pad_inches=.04)
 plt.close(fig)
# Figure 1: restrained, serif process diagram; conceptual rather than quantitative.
with plt.rc_context({'font.family':'STIXGeneral'}):
 f,ax=plt.subplots(figsize=(7,2.1))
 f.subplots_adjust(left=.01,right=.99,bottom=.02,top=.98)
 ax.set(xlim=(0,7),ylim=(0,2.1));ax.axis('off')
 ink='#252525'; muted='#555555'; rule='#B6B6B6'
 ax.text(.03,1.79,'Shared data and models',fontsize=11,fontweight='bold',color=ink)
 ax.text(.03,1.52,'Sequence and chemistry\nAssay context\nEndpoint predictors\nProvenance and partitions',
         fontsize=10,color=muted,va='top',linespacing=1.65)
 ax.plot([2.12,2.12],[.15,1.94],color=rule,lw=.7)
 def process(y,title,steps,feedback):
  ax.text(2.40,y,title,fontsize=11,fontweight='bold',color=ink)
  for x,label in zip([2.40,4.08,5.77],steps):
   ax.text(x,y-.37,label,fontsize=10,color=ink,va='center')
  for x in [3.53,5.20]:
   ax.add_patch(FancyArrowPatch((x,y-.37),(x+.37,y-.37),arrowstyle='->',
                 mutation_scale=9,linewidth=.8,color=muted))
  ax.text(2.40,y-.69,feedback,fontsize=9,color=muted)
 process(1.79,'a  Molecular design',
         ['Construct ASO','Score candidate','Update archive'],
         'Frozen predictions; predictor-query budget')
 ax.plot([2.4,6.96],[.98,.98],color=rule,lw=.55)
 process(.77,'b  Experimental selection',
         ['Select assay','Reveal result','Update belief'],
         'Recorded measurements; assay-cost budget')
 save(f,'architecture')
# Figure 2: verified report values, no fabricated learning-curve samples.
used += [ROOT/'docs/acquisition-comparison.md',ROOT/'docs/updates/2026-11-14-1150-est.md']
f,axs=plt.subplots(1,2,figsize=(7,2.05),gridspec_kw={'width_ratios':[1,1.35]})
ax=axs[0]; ax.axvline(0,color='#999999',lw=.8)
ax.errorbar([.0095],[0],xerr=[[.0095-.0043],[.0146-.0095]],fmt='o',capsize=4,color=COL['warm_start'])
ax.set(xlim=(-.002,.018),ylim=(-.7,.7),yticks=[],xlabel='Uncertainty − random, normalized AULC')
ax.set_title('(a) Huesken acquisition: 40 seeds',loc='left');ax.text(.0095,.23,'+0.0095 [0.0043, 0.0146]',ha='center',fontsize=8)
ax.text(.0095,-.30,'Paired p = 0.00095',ha='center',fontsize=8)
ax=axs[1]; labels=['One-hot\nRidge','Frozen FM\nRidge','Frozen FM\nhead','LoRA\nhead'];vals=[.4910,.3374,.2801,.4196]
ax.bar(np.arange(4),vals,color=[COL['greedy'],'#8A9299','#B5BDC1',COL['full']],width=.63)
for i,v in enumerate(vals):ax.text(i,v+.012,f'{v:.3f}',ha='center',fontsize=8)
ax.set(xticks=range(4),xticklabels=labels,ylim=(0,.57),ylabel='Held-out Pearson r');ax.set_title('(b) Huesken: 200 labels, 5 seeds',loc='left')
f.tight_layout(w_pad=2);save(f,'prediction')
# Figure 3: actual paid-query trajectories on original development targets.
a=read_json('artifacts/molecular-ppo-attribution-v1/analysis.json')
f,axs=plt.subplots(1,4,figsize=(7,1.8),sharex=True,sharey=True)
labels={'full':'Pretrain + PPO','warm_start':'Pretrain only','random':'Random','greedy':'Greedy'}
for ax,t in zip(axs,['FGFR4','F9','F12','TTR']):
 for m in labels:
  row=next(r for r in a['summaries'] if r['budget']==8 and r['target']==t and r['method']==m)
  ax.plot(range(1,9),row['mean_quality_by_request'],label=labels[m],color=COL[m],
          linestyle='--' if m=='warm_start' else '-',lw=1.7,marker='.' if m=='full' else None)
 ax.set(title=t,xticks=[1,4,8],ylim=(-.03,1.03),xlabel='Paid requests')
axs[0].set_ylabel('Best eligible utility')
f.legend(*axs[0].get_legend_handles_labels(),loc='upper center',ncol=4,bbox_to_anchor=(.5,1.15),frameon=False,fontsize=8)
f.tight_layout(w_pad=.7);save(f,'molecular')
# Figure 4: historical concentration readouts and a separate synthetic planning slice.
r=read_json('artifacts/adaptive-dose-response-v1/report.json')['roles']['assessment']
p=ROOT/'artifacts/value-of-planning-v1/grid.csv';used.append(p)
rows=list(csv.DictReader(p.open()))
f,axs=plt.subplots(1,2,figsize=(7,2.35),gridspec_kw={'width_ratios':[1.15,1]})
ax=axs[0]; names=['full_grid','fixed_early','information_gain','decision_aware'];v=[r['methods'][n]['mean_measurements'] for n in names]
ax.bar(range(4),v,color=['#8A9299',COL['warm_start'],COL['greedy'],COL['full']],width=.63)
for i,n in enumerate(names):
 d=r['methods'][n];ax.text(i,v[i]+.10,f'{v[i]:.3f}',ha='center',fontsize=8)
 ax.text(i,.12,f"{d['false_positive']}/{d['false_negative']}",ha='center',va='bottom',color='white',fontweight='bold',fontsize=9)
ax.set(xticks=range(4),xticklabels=['Full\ngrid','Fixed\nstop','Information\ngain','Decision\naware'],ylabel='Mean readouts / ASO',ylim=(0,5.2))
ax.set_title('(a) Historical assessment: 240 ASOs',loc='left')
ax=axs[1]; mat=np.zeros((3,3))
for i,u in enumerate([.1,.5,1.]):
 for j,c in enumerate([2,3,4]):
  row=next(x for x in rows if float(x['uncertainty'])==u and int(x['confirm_cost'])==c and int(x['budget'])==6 and float(x['prevalence'])==.5 and float(x['coupling'])==.75)
  mat[i,j]=float(row['planning_gain'])
im=ax.imshow(mat,cmap='YlOrBr',vmin=0,vmax=.25,aspect='auto')
for i in range(3):
 for j in range(3):ax.text(j,i,f'{mat[i,j]:.3f}',ha='center',va='center',color='white' if mat[i,j]>.17 else '#222222',fontsize=9)
ax.set(xticks=[0,1,2],xticklabels=['2','3','4'],yticks=[0,1,2],yticklabels=['0.1','0.5','1.0'],xlabel='Confirmation / screen cost',ylabel='Uncertainty setting u')
ax.set_title('(b) Synthetic optimal − greedy yield',loc='left')
f.tight_layout(w_pad=2.1);save(f,'measurement_planning')
# Source hashes enable verification without copying any hidden measurement labels.
manifest=[{'path':str(p.relative_to(ROOT)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(used))]
(PAPER/'evidence'/'figure-sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Generated four vector figures and source-hash manifest.')
