# Design surface

A local page that turns a gene symbol into a ranked panel of candidate antisense
oligonucleotides, scored by the project's measured endpoint predictors.

```sh
PYTHONPATH=src python app/server.py --port 8000
# then open http://127.0.0.1:8000
```

The server fits each endpoint predictor on all labelled rows of its dataset at
startup (about 10 seconds), then serves static files and a small JSON API. It needs
the pinned upstream environment, because the featurizers and models do.

## What it does

1. Resolves the gene to its canonical transcript via Ensembl REST and caches the
   cDNA under `artifacts/transcripts/` (gitignored), so later runs work offline.
   A transcript can also be pasted in directly, which needs no network at all.
2. Tiles every window of the transcript and takes the reverse complement, giving one
   candidate ASO per start site.
3. Builds each candidate in a chemistry that **matches a training set exactly**:
   `ps_moe_gapmer` is the 19-mer 5-10-4 PS/2'-MOE design that dominates
   `MOE_Neurotox_1`, and `ps_2ome_gapmer` is the 20-mer 5-10-5 PS/2'-OMe design of
   the Alharbi TLR screens. The fitted featurizers have fixed widths, so a candidate
   outside the design cannot be encoded at all.
4. Scores each candidate with the endpoint models **whose chemistry it matches**, and
   withholds the others rather than extrapolating across chemistry.
5. Computes label-free sequence flags: CpG count, distance from the 3' end to the
   nearest guanine, longest G run, GC fraction, ViennaRNA self-structure, and the
   target site's mean unpaired probability in local context.

## What it deliberately does not do

- **No efficacy prediction.** The project's efficacy model is fitted on Huesken
  siRNA, a different modality that must not be applied to ASO candidates, and no ASO
  efficacy endpoint has been trained. The page says so rather than letting a safety
  ranking read as a potency ranking.
- **No combined score.** Endpoints stay in their own units.
- **No structure prediction.** The 3D view is an idealized A-form helix drawn from
  the sequence, so it shows length, register and gapmer architecture and nothing
  else. The PDB download carries that warning in its REMARK records and opens in
  PyMOL.
- **No claim that any candidate works.** Everything generated is an unvalidated
  hypothesis.

## Honesty panel

The page leads with how far the panel sits outside the training data, because for a
gene the models have never seen that is the most important fact about the numbers:
the share of predictions outside the measured label range, the median novelty
percentile, and the rank correlation between the predictions and the published
guanine-proximity rule the model was never given.

## API

| Route | Returns |
| --- | --- |
| `GET /api/meta` | chemistries, endpoint specs per chemistry, non-claims |
| `GET /api/design?gene=&chemistry=&step=&limit=&sort=` | transcript, ranked rows, summary |
| `POST /api/design` | the same, with `{"sequence": "..."}` for a pasted transcript |
| `GET /api/panel.csv?...` | the ranked panel as CSV, with its caveats in the header |
| `GET /api/structure?sequence=&chemistry=` | the idealized duplex as PDB |

The front end is three static files with one CDN dependency (3Dmol.js) and no build
step, so it can be hosted anywhere the API is reachable.
