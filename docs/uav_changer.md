## UAV Switching API

### Overview
Utility helpers to switch the active UAV model by updating simulator settings, restarting the editor, and refreshing the in-memory UAV handle.

### Quick Start
```python
from utils.UAV_changer import change_UAV
from utils.UAV import UAV

uavs = [UAV()]                           # managed list with one active UAV
changed = change_UAV(uavs, "Matrice200")  # switch to Matrice200
print("changed", changed)
```

### API Reference

Name and settings helpers
- `change_name(uav, name) -> None` — Set the UAV name if valid, else fallback to default.
- `update_UAV_settings(uav, vehicle_name) -> None` — Write a single-vehicle config (SimpleFlight) into the simulator settings file referenced by `uav.get_airsim_json_path()`.

High-level switch
- `change_UAV(uav_list: list, name: str) -> bool`
  - Early-exit if the current UAV name already equals `name`.
  - Disconnects if connected, updates name and settings, restarts the editor using the current map’s `.bat`, and replaces `uav_list[0]` with a fresh `UAV()` instance.
  - Returns `True` when a change is applied.

### Examples

Switch and reconnect flow
```python
from utils.UAV_changer import change_UAV
from utils.UAV import UAV

uavs = [UAV()]
if change_UAV(uavs, "sampleflyer"):
    # new UAV object is in uavs[0]; reconnect as needed
    new_uav = uavs[0]
    # new_uav.connect(); new_uav.take_off(); ...
    pass
```

### Tips
- Requires write permission to the simulator `settings.json` path exposed by your UAV object.
- Restarting the editor can take time; ensure you wait for startup before reconnecting to the new UAV.


