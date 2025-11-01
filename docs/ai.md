## Gemini Command Conversion API

### Overview
Wrapper that converts natural language into shell-like UAV commands for this project. It maintains a lightweight chat session and outputs a plain command string (backticks removed) or `None` on failure.

### Quick Start
```python
from ai.ai_config import GeminiDroneController

controller = GeminiDroneController(api_key="<YOUR_API_KEY>")
cmd = controller.convert_to_command("Fly to (10,20,-10) at 3 m/s")
print(cmd)  # e.g., fly_to_position --target "(10,20,-10)" --velocity 3
```

### API Reference

Class: `GeminiDroneController`
- `__init__(api_key: str)`
  - Initializes the model client and seeds the conversation with project-specific system prompts.
- `convert_to_command(user_input: str) -> Optional[str]`
  - Converts a natural-language request into a command string suitable for your command registry.
  - Returns `None` on errors (e.g., network issues, invalid response).

### Examples

Route generated command into your executor
```python
from ai.ai_config import GeminiDroneController
from utils.CommandDecorator import CommandRegistry

controller = GeminiDroneController(api_key="<KEY>")
command = controller.convert_to_command("Take off and fly to (0,0,-10)")
if command:
    # lookup and execute within your app's registry
    # executor.execute(command)
    print("COMMAND:", command)
```

Handle invalid or unsafe output
```python
command = controller.convert_to_command("do something crazy")
if not command:
    print("No valid command produced")
else:
    # validate against allowed commands before execution
    allowed = CommandRegistry().get_registered_commands().keys()
    base = command.split()[0] if command else ""
    if base not in allowed:
        print("Rejected unknown command:", base)
```

### Tips
- Command validation is not enforced in the wrapper. Validate against `CommandRegistry` before executing.
- Prompts are seeded via `UAVPrompts.SYSTEM_PROMPT`; keep your decorators and prompt guidelines in sync.
- The wrapper strips backticks to simplify downstream parsing.