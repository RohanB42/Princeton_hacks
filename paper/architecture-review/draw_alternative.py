"""Standalone diagram alternative; does not alter the manuscript or its figures."""
from pathlib import Path
import os
HERE = Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR'] = str(HERE / '.mplconfig')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

with plt.rc_context({'font.family':'STIXGeneral','font.size':10,'svg.fonttype':'none'}):
    fig, ax = plt.subplots(figsize=(7, 1.45))
    fig.subplots_adjust(left=.015,right=.985,bottom=.025,top=.98)
    ax.set(xlim=(0,7),ylim=(0,1.45)); ax.axis('off')
    ink='#242424'; muted='#666666'
    for offset,title,steps,budget in [
        (0,'Molecular design',['Propose\nmolecule','Predict\nproperties','Update\nshortlist'],'Budget: model evaluations'),
        (3.6,'Experimental selection',['Choose\nassay','Reveal\nmeasurement','Update\nestimates'],'Budget: assay purchases')]:
        xs=[offset+.45,offset+1.65,offset+2.85]
        ax.text(offset+1.65,1.31,title,ha='center',va='center',fontsize=11,fontweight='bold',color=ink)
        ax.text(offset+1.65,1.09,budget,ha='center',fontsize=9,color=muted)
        for x,label in zip(xs,steps):
            ax.text(x,.73,label,ha='center',va='center',fontsize=10,color=ink,linespacing=1.05)
        for start in [offset+.90,offset+2.08]:
            ax.add_patch(FancyArrowPatch((start,.73),(start+.32,.73),arrowstyle='->',mutation_scale=9,lw=.9,color=ink))
        # Feedback loop, kept visually separate from the forward process.
        ax.plot([xs[2],xs[2],xs[0]],[.48,.27,.27],lw=.8,color=muted)
        ax.add_patch(FancyArrowPatch((xs[0],.27),(xs[0],.49),arrowstyle='->',mutation_scale=9,lw=.8,color=muted))
        ax.text(offset+1.65,.08,'Next decision',ha='center',fontsize=9,color=muted)
    ax.plot([3.48,3.48],[.15,1.39],color='#CCCCCC',lw=.6)
    fig.savefig(HERE/'decision-loops.svg',bbox_inches='tight',pad_inches=.04,metadata={'Creator':'OLIGARCH diagram alternative'})
    fig.savefig(HERE/'decision-loops.png',dpi=220,bbox_inches='tight',pad_inches=.04)
print('Wrote separate SVG and PNG alternatives; live manuscript unchanged.')
