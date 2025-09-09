## UAV Control and Telemetry API

### Overview
This document describes our wrapper surface only (no raw simulator APIs). `UAVController` exposes a stable, user-friendly interface for connection, flight, imaging, camera control, telemetry, and XML logging/monitoring.

### Coordinate Frames
- NED: X forward, Y right, Z down. Use negative Z to ascend. The wrapper handles conversions as needed; callers can think in `(front, right, down)` for velocity helpers.

### Quick Start
```python
from utils.UAV_controller import UAVController

uav = UAVController()
uav.connect()                              # enable control for the default UAV
uav.take_off()
uav.move_by_velocity_face_direction(2, 0, 0, 2)
frame = uav.get_origin_frame()             # get UAV main viewpoint images (numpy HxWx3 uint8)
uav.land()
uav.disconnect()
```

### API Reference

Connection & lifecycle
- `connect()` — Prepare the default UAV for control.
- `disconnect()` — Safely release control resources.
- `stop()` — Convenience stop (lands).
- `take_off()` / `land()` / `hover()` — Basic flight primitives; `*_async` variants return immediately.

Motion primitives (body-frame friendly)
- `move_by_velocity_face_direction(v_front, v_right, vz, duration)` — Move while facing the velocity direction.
- `move_by_velocity_with_same_direction(v_front, v_right, vz, duration, yaw_mode)` — Move without changing body yaw.
- `move_by_velocity_new(vx, vy, vz, duration)` — Direct velocity command in world frame.
- `fly_to_position(target: tuple[float,float,float], velocity=2.0)` — Fly to `(x,y,z)` at a given speed.

Imaging
- `get_origin_frame() -> np.ndarray` — Current main camera image (HxWx3 uint8).
- `set_capture_type(types: list[str])` — Select image kinds to fetch, e.g., `["Scene", "DepthVis", "Segmentation"]`.
- `get_all_frame() -> dict[str, np.ndarray]` — Batch-fetch frames for the chosen types.

Camera
- `set_camera_rotate(rad)` / `get_camera_rotation()` — Set/get pitch rotation.
- `rotate_camera(rate, duration)` / `rotate_camera_async(...)` — Incrementally adjust camera pitch over time.

Telemetry
- `get_body_eularian_angle()` — UAV body angles `(pitch, roll, yaw)`.
- `get_camera_eularian_angle()` — Camera angles `(pitch, roll, yaw)`.
- `get_body_position()` / `get_camera_position()` — Positions `(x, y, z)`.
- `get_velocity()` / `get_angular_velocity()` — Linear and angular velocity tuples.

Pose utilities
- `set_position_directly((x,y,z), (pitch,roll,yaw)=(0,0,0)) -> bool` — Instantly place UAV pose.

Configuration & limits
- `get_instruction_duration()`, `set_instruction_duration(sec)` — Control command granularity.
- `get_max_velocity()`, `get_max_rotation_rate()` — Motion caps.
- `get_resolution_ratio()`, `get_FOV_degree()` — Imaging parameters.
- `get_airsim_json_path()` — Path to the simulator settings.
- `get_uav_name_list()`, `get_name()`, `set_name(name)` — UAV naming utilities.

Logging & monitoring
- `start_logging(recording_interval=0.2)` / `stop_logging() -> str` — Structured flight logs to `data/state_logs/`.
- `start_monitoring(monitoring_interval=0.2)` / `stop_monitoring() -> str` — Lightweight monitoring snapshots.

Misc
- `get_frame()` / `set_frame(frame)` — Store/retrieve the last captured frame snapshot.
- `get_move_flag()` / `set_move_flag(bool)` — App-level motion state toggles.

### Examples

Capture multiple image kinds at once (wrapper)
```python
uav = UAVController(); uav.connect(); uav.take_off()

# set multiple images
uav.set_capture_type(["Scene", "DepthVis", "Segmentation"])  # select wrapper-supported kinds

# get images at once
frames = uav.get_all_frame()
scene = frames["Scene"]              # HxWx3 uint8
depth_vis = frames["DepthVis"]       # HxWx3 uint8
seg = frames["Segmentation"]         # HxWx3 uint8

uav.land(); uav.disconnect()
```

Fly to a position and persist a log
```python
uav = UAVController(); uav.connect(); uav.take_off()

# start to log the uav flying path
uav.start_logging(0.2)

# fly to a position with 3m/s
uav.fly_to_position((10, 0, -5), velocity=3.0)

# stop logging and save
xml_str = uav.stop_logging()  # file also written under data/state_logs/


uav.land(); uav.disconnect()
```

Teleport and adjust camera pitch
```python
uav = UAVController(); 
# connect and take off
uav.connect(); 
uav.take_off()
# set uav to a position directly
uav.set_position_directly((0, 0, -10), (0, 0, 0))
# rotate camera
uav.rotate_camera(-0.5, 1.0)  # ~-28.6 degrees

uav.land(); uav.disconnect()
```

### Tips
- Call `connect()` before issuing flight or imaging commands; call `disconnect()` when done.
- Use negative Z to ascend (e.g., `-5`).
- `*_async` variants return immediately; use sync forms when you need blocking behavior.


