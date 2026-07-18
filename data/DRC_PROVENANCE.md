# DRC seeded-field demo asset provenance

## Local asset

| Field | Value |
|---|---|
| Dataset | Demining Research Community Seeded Field Multimodal Landmine Detection Dataset, v2 |
| Dataset DOI | [10.5281/zenodo.19100554](https://doi.org/10.5281/zenodo.19100554) |
| License | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Downloaded | 2026-07-18 |
| File | `3-1_Field1_RGB_PreBurial_ortho_georeferenced_transparent.tif` |
| SHA-256 | `9deb1da62bd68df49c81fe125bf6b89eb6a936e051a71966dfcd90be7c2df14a` |
| Collection | DRC / Baur & Steinberg, Site 1, June 12–16 2023; Autel EVO II Dual RGB, 12 m AGL, pre-burial |
| Raster | GeoTIFF, 13,717 × 22,790 px, 4 `uint8` bands, EPSG:4326 |

The local binary is intentionally stored under `data/raw/drc/`, which is
ignored by Git. Any screenshot, derivative, or publication using it must credit
the Demining Research Community dataset and link its DOI and CC BY 4.0 license.

## Ground-truth status

The DRC describes precisely documented target locations, but the Zenodo record
does not expose a ready-to-use object-detection annotation file or YOLO labels.
This orthomosaic is approved for provenance-controlled UI and GeoTIFF workflow
validation. It is **not approved for supervised training** until a released
target-coordinate artifact is located or the DRC confirms permission and
provides the corresponding ground truth.

Do not infer training labels from the imagery alone or report detection metrics
using this asset until that decision gate is resolved.
