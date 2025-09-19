## Dataset Collection API

### Overview
WARNING: While you can collect images via the APIs in `UAVController`, using this standalone dataset collector provides faster throughput and more consistent data quality.
High-level dataset collection helpers that move the UAV, capture multi-modal images, validate segmentation frames, and trigger per-sample annotations. Designed to work with this project’s folder layout and post-processing pipeline.

### Key Paths
- Images root: `data/capture_imgs/`
  - `SceneImage/`, `SegmentationImage/`, `DepthPlanarImage/`, `DepthPerspectiveImage/`, `DepthVisImage/`, `SurfaceNormalsImage/`, `InfraredImage/`
- Annotations: `data/Annotation/` (via `utils.processcopy.generate_annotation`)

### Quick Start
```python
from utils import fly
import airsim

client = airsim.MultirotorClient()
client.confirmConnection()

# collect one pass of multi-height / multi-angle captures; 
# map_name, vehicle_name is used in picture name (not control with real UE map)
num_sets = fly.collect_dataset(client, map_name="Brushify", vehicle_name="Default")
print(f"Captured sets: {num_sets}")
```

### API Reference

Directory utilities
- `ensure_directories_exist() -> None` — Create required folders for all modalities if missing.

Main workflow
- `collect_dataset(client, map_name, vehicle_name="") -> int`
  - Ensures directories exist, connects/arms/takes off, performs stepwise moves, and calls `image_capture`.
  - Returns the number of valid image sets captured.

Capture internals
- `image_capture(picture_num, capture_num, client, map_name, picture_nums) -> int`
  - For each step: climbs through heights `(j+1)*5` meters and rotates across 19 angles (5° increments).
  - Captures the following per angle: `Scene`, `Segmentation`, `SurfaceNormals`, `Infrared`, `DepthPerspective`, `DepthPlanar`, `DepthVis`.
  - If segmentation is judged empty, deletes this set across all modalities and skips annotation.

Validation & cleanup
- `is_segmentation_empty(response, black_threshold=0.9985, pixel_threshold=10) -> bool` — Heuristic to filter empty segmentation frames.
- `delete_images(filename) -> None` — Remove a set of files (same `filename`) across all modality folders.

Filenames
- Scene template: `Scene{global_index}_{height}_{angle_deg}_{map}.png`.
- Other modalities reuse the exact same `filename` in their respective directories.

### Examples

Collect and then post-process annotations automatically
```python
from utils import fly
from utils import processcopy
import airsim

client = airsim.MultirotorClient(); client.confirmConnection()

# run collection (returns count of valid sets)
n = fly.collect_dataset(client, map_name="Brushify", vehicle_name="Default")

# optional: run annotation generation for existing segmentation images
# (collect_dataset already triggers per-sample annotation; this is for re-run scenarios)
ok = processcopy.generate_annotation("Scene1_5_0_Brushify.png")
print("one-off annotation ok?", ok)
```

Batch collection with stricter filtering
```python
from utils import fly
import airsim

client = airsim.MultirotorClient(); client.confirmConnection()

# first call ensures folders exist
fly.ensure_directories_exist()

# collect with a custom map tag and vehicle
count = fly.collect_dataset(client, map_name="beach", vehicle_name="Default")
print("valid sets:", count)
```

### Tips
- You can further process results with `utils/processcopy.py` to (re)generate XML annotations under `data/Annotation/`.
- If a segmentation image is mostly black, the whole set is automatically discarded to keep the dataset clean.
- Ensure your AirSim instance is running and the chosen `vehicle_name` exists in settings.
