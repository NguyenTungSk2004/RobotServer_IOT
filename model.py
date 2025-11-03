import asyncio
from dataclasses import dataclass

@dataclass
class Action:
    action_id: str
    intent: str
    params: dict

    def to_dict(self):
        return {
            "action_id": self.action_id,
            "intent": self.intent,
            "params": self.params
        }

@dataclass
class PendingAction:
    data: Action
    future: asyncio.Future
    created_at: float