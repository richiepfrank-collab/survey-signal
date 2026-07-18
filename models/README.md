# Local model artifacts

Model binaries are never committed. Survey Signal loads only a local model directory
supplied through `MINEMARK_MODEL`; it never downloads weights while serving.

## Staged baseline

| Field | Value |
|---|---|
| Model | PekingU `rtdetr_r18vd` |
| Source | <https://huggingface.co/PekingU/rtdetr_r18vd> |
| License | Apache-2.0 |
| `model.safetensors` SHA-256 | `fe87a5a30f5daf298d10794c7682a63b6107986f97d6a770ba948d89e4340093` |
| Runtime | Hugging Face Transformers RT-DETR |
| Intended role | Generic COCO proposal baseline only; not an ordnance detector |

The checkpoint is locally staged at `models/rtdetr-r18vd/` for development and
ignored by Git. Before a release or demo, record its exact revision and
SHA-256 in the submission evidence.

To stage it on a connected preparation machine:

```bash
python scripts/stage_model.py --repo PekingU/rtdetr_r18vd --out models/rtdetr-r18vd
```

Then run Survey Signal offline:

```bash
MINEMARK_MODEL=models/rtdetr-r18vd minemark serve
```
