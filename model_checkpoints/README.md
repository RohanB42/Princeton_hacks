# Preserved prediction checkpoints

Published at the user's explicit request on November 14, 2026. These are copies of
existing trained prediction artifacts, not new training runs or a newly selected
best model. The removed target-window RL scaffold and its policy weights are not
included. Source files in the local research worktrees remain unchanged.

`manifest.json` records every file's byte count, SHA-256, family and compatible
loader-code revision. A compatible revision is not automatically the revision at
which a historical training run was executed. Available Atlas receipt metadata and
receipt hashes are included without copying complete generated experiment reports.

| Directory | Contents | Loading requirements |
|---|---|---|
| `supported-aso-v1/` | Complete fitted one-hot Ridge JSON, 2,000 source labels, exact 20-mer MOE efficacy profile | Current `oligo_engine.reward.portable.PortableEfficacy`; exact assay/chemistry gate |
| `atlas-scaling-v1/` | Frozen and LoRA source/target heads, selected and intermediate epoch snapshots, classical source models | `codex/atlas-lora-scaling` at `f197d79`; its research runtime, matching feature/context schema and RNA-FM backbone for neural heads |
| `atlas-fm-development-v1/` | Earlier frozen-chemistry and LoRA-chemistry source snapshots | `codex/atlas-rnafm-research` at `9fd9f10`; its research runtime and backbone |
| `huesken-lora-proof-seed300/` | Frozen-head and LoRA-head proof checkpoints | `models/rnafm_lora.py` adapter loader, matching saved configuration and RNA-FM backbone |

The Atlas classes and loading procedures have not been merged wholesale into main.
Use their pinned research code; uploading snapshots does not create a generic
deployment API. Torch snapshots contain custom feature/context objects; classical
files use pickle. Verify their hashes and use the matching trusted project loaders
and versions. The portable JSON efficacy model requires no pickle loading.

## External pretrained backbone

The downloaded `RNA-FM_pretrained.pth` is 1.2 GB and remains an external dependency,
not an ordinary Git blob. This is the pretrained upstream backbone, not one of our
task-adapted checkpoints. The existing loader pins:

- Source: <https://huggingface.co/cuhkaih/rnafm/resolve/main/RNA-FM_pretrained.pth>
- SHA-256: `5b5d7d87b37c291ef42c140ef9edf7aea29f255fa2a4fd435f776c52e93d5e99`
- RNA-FM source revision: `348951516e0963d22bbb33b3c9fc18c89081d38e`

The local backbone was checked against that hash during publication. A future
download must also match; the URL's `main` ref alone is not a version guarantee.
The existing verified loader is `src/oligo_engine/representations/rnafm.py`.

## Integrity check

Run from the repository root without loading any serialized model:

```sh
python - <<'PY'
import hashlib
import json
from pathlib import Path

root = Path("model_checkpoints")
manifest = json.loads((root / "manifest.json").read_text())
for entry in manifest["checkpoints"]:
    raw = (root / entry["path"]).read_bytes()
    assert len(raw) == entry["bytes"], entry["path"]
    assert hashlib.sha256(raw).hexdigest() == entry["sha256"], entry["path"]
print(f"Verified {len(manifest['checkpoints'])} checkpoint files")
PY
```

No checkpoint is asserted to provide clinical safety, validated generated-ASO
efficacy or new target generalization merely because it is preserved here. Retain
the original study's split and training-membership restrictions when evaluating
these models. Published model weights are not a clean held-out evaluation set.
