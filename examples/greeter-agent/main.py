import json
import os

CFG_PATH = os.path.join(os.path.dirname(__file__), "agent_config.json")

def load_config():
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"name": "greeter-agent"}

if __name__ == "__main__":
    cfg = load_config()
    print(f"Hello from {cfg.get('name','greeter-agent')}! 🌱 A minimal example agent is running.")
