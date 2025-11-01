## Map Configuration and Launch API

### Overview
Manages the current map selection, persists it to `settings/map.json`, and launches/refreshes UE via a `.bat` file.

### Configuration File
- Default path in code: `settings/map.json`
- Keys:
  - `map`: current map name
  - `start_map_batfile`: absolute path to the UE launch `.bat`
  - `map_list`: available maps

### Public API

#### class MapController
Encapsulates map state and operations.

Properties (via getters):
- `get_map_name() -> str`
- `get_map_batfile() -> str`
- `get_map_list() -> list[str]`

Methods:
- `set_map(map_name: str) -> None`
  - Sets current map and updates `start_map_batfile` to `Shell/<map_name>.bat` (Windows path).
  - Persists to JSON.

- `start_map(name: str | None) -> bool`
  - If `name` equals current map, returns False (no-op).
  - If `name` exists in `map_list`, calls `set_map(name)` and restarts UE using `restart_UE(get_map_batfile())`.
  - Returns True if a restart is triggered.

### Usage Example
```python
from utils.map_controller import MapController

mc = MapController()
print(mc.get_map_name())
mc.start_map("Brushify")
```

### Notes
- Ensure `.bat` files exist under `Shell/` and point to valid `UE4Editor.exe` and `UAV.uproject`.
- `restart_UE` is provided by `utils.utils` and should be configured for your environment.



