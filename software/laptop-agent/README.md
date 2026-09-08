# ADAM Companion Laptop Agent

The **ADAM Laptop Agent** is a lightweight background companion service that runs on your local workstation (macOS, Windows, or Linux). It bridges ADAM's cloud voice intelligence with your local computer, allowing ADAM to control system audio volume, screen brightness, lock the screen, control media playback (Spotify), open applications, and query battery telemetry.

---

## ⚡ Architecture: Modular Action Registry

Unlike monolithic control services with brittle `if/elif` command chains, the Laptop Agent uses a **self-describing decorator pattern**:
```python
@action(
    description="Set the workstation master audio volume (0-100%)",
    params={"level": ("integer", "Volume percentage between 0 and 100", True)}
)
def set_volume(level: int) -> dict:
    # OS-specific implementation
    return {"status": "ok", "volume": level}
```

When the Raspberry Pi boots up, it queries `GET /actions` over the LAN. The Laptop Agent returns the complete JSON schema of all registered functions, allowing the Pi to register them as **Google Gemini Function Calling tools automatically**.

---

## 📂 Source Code Structure

```text
software/laptop-agent/
├── README.md               # Setup and architecture guide
├── requirements.txt        # Host OS dependencies
└── src/
    └── laptop_agent.py     # Flask REST server & Action Registry
```

---

## 🛠️ Setup & Running

### 1. Installation
```bash
cd software/laptop-agent
python -m venv venv

# Windows
.\venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configuration (.env)
Create a `.env` file in `software/laptop-agent`:
```env
AGENT_PORT=5000
AGENT_TOKEN=change_this_secret_token_in_production
```

### 3. Launch
```bash
python src/laptop_agent.py
```
The agent will announce itself on your local Wi-Fi network via **Zeroconf (mDNS)** as `_adam-agent._tcp.local.`. ADAM's Raspberry Pi brain will discover it automatically without requiring manual IP address configuration.

---

## 🔌 API Reference

### `GET /actions`
Returns the self-describing tool manifest:
```json
{
  "version": "2.0",
  "actions": {
    "set_volume": {
      "description": "Set the workstation master audio volume (0-100%)",
      "parameters": {
        "type": "object",
        "properties": {
          "level": {"type": "integer", "description": "Volume percentage between 0 and 100"}
        },
        "required": ["level"]
      }
    }
  }
}
```

### `POST /control`
Executes an action:
- **Headers**: `Authorization: Bearer <AGENT_TOKEN>`, `Content-Type: application/json`
- **Body**:
  ```json
  {
    "action": "set_volume",
    "params": {"level": 65}
  }
  ```
- **Response**:
  ```json
  {
    "status": "ok",
    "result": {"status": "ok", "volume": 65}
  }
  ```
