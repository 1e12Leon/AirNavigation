## Weather Control API

### Overview
Minimal wrapper to enable and adjust simulated weather. Stores the current weather type and intensity (0–100) and applies the change immediately.

### Quick Start
```python
from utils.weather_controller import WeatherController

wc = WeatherController()
wc.change_weather('rain', 60)
print(wc.get_weather())  # ('rain', 60)
```

### API Reference

Class: `WeatherController`
- Constructor: initializes control and enables the weather system.

Methods
- `get_weather() -> tuple[str, int]`
  - Returns `(weather_type, value)` where `value ∈ [0,100]`.
- `change_weather(weather_type: str, val: int) -> None`
  - Resets all weather parameters to 0, then sets the specified type with strength `val / 100`.
  - Supported: `'rain'`, `'snow'`, `'dust'`, `'Fog'`.

### Examples

Switch weather types during a session
```python
wc = WeatherController()
wc.change_weather('snow', 30)
wc.change_weather('dust', 50)
wc.change_weather('Fog', 80)
```

### Tips
- Use lowercase for `rain`, `snow`, `dust`, and capitalized `Fog` as implemented.
- Apply moderate values (30–60) for testing visibility without fully obscuring the scene.


