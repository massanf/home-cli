import json

import anthropic

from .hue import HueCode
from .presets import apply_preset
from .state import get_device_state, save_snapshot, update_device_state
from .switchbot import SwitchBotCode

MODEL = "claude-opus-4-7"

TOOLS = [
    {
        "name": "control_curtain",
        "description": "Open or close the curtains. Use quietopen/quietclose for slow, silent movement.",  # noqa: E501
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["open", "close", "quietopen", "quietclose"],
                    "description": "open/close for normal speed, quietopen/quietclose for quiet mode",  # noqa: E501
                }
            },
            "required": ["state"],
        },
    },
    {
        "name": "control_globe",
        "description": "Turn the globe light on or off.",
        "input_schema": {
            "type": "object",
            "properties": {"state": {"type": "string", "enum": ["on", "off"]}},
            "required": ["state"],
        },
    },
    {
        "name": "control_edison",
        "description": "Turn the Edison bulb light on or off.",
        "input_schema": {
            "type": "object",
            "properties": {"state": {"type": "string", "enum": ["on", "off"]}},
            "required": ["state"],
        },
    },
    {
        "name": "control_hue",
        "description": (  # noqa: E501
            "Set the Philips Hue lights to a preset. 'on' is normal bright, "
            "'off' turns them off, 'bar' is warm ambient, 'dim' is low warm light, "
            "'theatre' is minimal for projector use."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "preset": {
                    "type": "string",
                    "enum": ["on", "off", "bar", "dim", "theatre"],
                }
            },
            "required": ["preset"],
        },
    },
    {
        "name": "control_ac",
        "description": "Control the air conditioner. Mode: 1=auto, 2=cool, 5=heat.",
        "input_schema": {
            "type": "object",
            "properties": {
                "on": {"type": "boolean"},
                "temperature": {
                    "type": "integer",
                    "description": "Target temperature in Celsius (16-30)",
                },
                "mode": {
                    "type": "integer",
                    "enum": [1, 2, 5],
                    "description": "1=auto, 2=cool, 5=heat",
                },
            },
            "required": ["on"],
        },
    },
    {
        "name": "apply_preset",
        "description": (
            "Apply a named scene preset. "
            "all-lights-on: all lights on. "
            "all-lights-off: all lights off. "
            "bar-mode: fancy warm ambient. "
            "globe-mode: globe only, hue dim. "
            "theatre-mode: close curtains, all lights off except minimal hue. "
            "dim: all switchbot off, hue dim."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "enum": [
                        "all-lights-on",
                        "all-lights-off",
                        "bar-mode",
                        "globe-mode",
                        "theatre-mode",
                        "dim",
                    ],
                }
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_status",
        "description": "Get the current state of all devices.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _execute_tool(name: str, inputs: dict) -> dict:
    if name == "control_curtain":
        state = inputs["state"]
        sb = SwitchBotCode()
        if state == "quietopen":
            sb.set_curtain_quiet(True)
            canonical = "open"
        elif state == "quietclose":
            sb.set_curtain_quiet(False)
            canonical = "close"
        else:
            sb.set_curtain(state == "open")
            canonical = state
        update_device_state("switchbot", "curtain", canonical)
        save_snapshot()
        return {"ok": True, "curtain": canonical}

    if name == "control_globe":
        state = inputs["state"]
        SwitchBotCode().set_globe(state == "on")
        update_device_state("switchbot", "globe", state)
        save_snapshot()
        return {"ok": True, "globe": state}

    if name == "control_edison":
        state = inputs["state"]
        SwitchBotCode().set_edison(state == "on")
        update_device_state("switchbot", "edison", state)
        save_snapshot()
        return {"ok": True, "edison": state}

    if name == "control_hue":
        preset = inputs["preset"]
        HueCode().apply_preset(preset)
        update_device_state("hue", "preset", preset)
        save_snapshot()
        return {"ok": True, "hue": preset}

    if name == "control_ac":
        on = inputs["on"]
        current = get_device_state("switchbot", "ac") or {}
        temp = inputs.get("temperature", current.get("temp", 25))
        mode = inputs.get("mode", current.get("mode", 1))
        fan = current.get("fan", 1)
        SwitchBotCode().set_ac(temp, mode, fan, on)
        update_device_state(
            "switchbot", "ac", {"on": on, "temp": temp, "mode": mode, "fan": fan}
        )
        save_snapshot()
        return {"ok": True, "ac": {"on": on, "temp": temp, "mode": mode}}

    if name == "apply_preset":
        apply_preset(inputs["name"])
        return {"ok": True, "preset": inputs["name"]}

    if name == "get_status":
        from .state import load_state

        return load_state()

    return {"error": f"Unknown tool: {name}"}


def run_llm_command(prompt: str, api_key: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    messages = [{"role": "user", "content": prompt}]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=(
                "You are a home automation assistant. "
                "Use the available tools to fulfill the user's request. "
                "Be concise in your final response — one sentence confirming what was done."  # noqa: E501
            ),
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = next(
                (b.text for b in response.content if hasattr(b, "text")), "Done."
            )
            return text

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = _execute_tool(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    }
                )

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
