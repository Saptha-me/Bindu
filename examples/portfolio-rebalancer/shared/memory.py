# shared/memory.py

class SemanticMemory:
    def __init__(self):
        self.store = {
            "risk_tolerance": "medium",
            "preferences": {
                "low_trade_frequency": False
            },
            "history": []
        }

    def get(self) -> dict:
        return self.store.copy()

    def update(self, new_data: dict):
        if not new_data:
            return

        # merge shallow keys
        for key, value in new_data.items():
            if key == "history":
                self.store["history"].append(value)
            else:
                self.store[key] = value