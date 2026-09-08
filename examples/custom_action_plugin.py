"""
custom_action_plugin.py — Extending the ADAM Laptop Agent
==============================================================================
ADAM AI Example Suite — DGEN Technologies Pvt. Ltd.

Demonstrates how to add custom skills to your ADAM Laptop Companion Agent
using the modular @action decorator pattern.

Adding a new tool takes only 1 function definition. When the Laptop Agent starts,
ADAM discovers these functions automatically and registers them as Google Gemini
tool-calling capabilities.
"""

from typing import Dict, Any

# Mock action registry decorator for demonstration purposes
ACTIONS = {}

def action(description: str, params: Dict[str, tuple] = None):
    """
    Decorator that registers a function into the Laptop Agent manifest.
    
    Args:
        description: Plain-English explanation of what this tool does.
                     Gemini uses this to know WHEN to call your tool.
        params: Dict of parameter_name -> (type_str, description_str, is_required)
    """
    def decorator(fn):
        name = fn.__name__
        ACTIONS[name] = {
            "fn": fn,
            "description": description,
            "params": params or {}
        }
        return fn
    return decorator


# ==============================================================================
# Example 1: Smart Home / Phillips Hue Light Controller
# ==============================================================================
@action(
    description="Control the color and brightness of desk smart lights.",
    params={
        "color": ("string", "Color name or hex code (e.g. 'warm white', 'blue', '#FF5500')", True),
        "brightness": ("integer", "Brightness level from 1 to 100 percent", False)
    }
)
def set_smart_light(color: str, brightness: int = 100) -> Dict[str, Any]:
    """Sets desk ambient light color and brightness."""
    print(f"[SmartLight] Setting color to '{color}' at {brightness}% brightness...")
    # Add your Philips Hue, Tuya, or Home Assistant API call here!
    return {
        "status": "success",
        "color": color,
        "brightness": brightness
    }


# ==============================================================================
# Example 2: Slack / Discord Quick Status Updater
# ==============================================================================
@action(
    description="Update the user's Slack or Discord presence status.",
    params={
        "status_text": ("string", "Status message text (e.g. 'In deep work', 'Lunch')", True),
        "emoji": ("string", "Status emoji shortcode (e.g. ':coffee:', ':rocket:')", False)
    }
)
def update_chat_status(status_text: str, emoji: str = ":robot_face:") -> Dict[str, Any]:
    """Updates team chat status."""
    print(f"[ChatStatus] Set status: '{emoji} {status_text}'")
    return {
        "status": "updated",
        "message": status_text,
        "emoji": emoji
    }


# ==============================================================================
# Verification & Manifest Inspection
# ==============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("  ADAM Action Plugin Schema Inspector")
    print("=" * 60)
    for name, spec in ACTIONS.items():
        print(f"\nTool Name   : {name}")
        print(f"Description : {spec['description']}")
        print("Parameters  :")
        for p_name, (p_type, p_desc, req) in spec["params"].items():
            req_str = "Required" if req else "Optional"
            print(f"  - {p_name} ({p_type}, {req_str}): {p_desc}")

    print("\nExecuting set_smart_light('cyan', 80):")
    res = ACTIONS["set_smart_light"]["fn"](color="cyan", brightness=80)
    print("Result:", res)
