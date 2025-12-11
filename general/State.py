from typing import TypedDict, Optional, List, Dict, Any

class IntentState(TypedDict, total=False):
    intent: str
    parameters: Dict[str, Any]
    status: Optional[str]  # 'in_progress' یا 'completed'

class ChatState(TypedDict):
    token: str
    # thread_id: str
    input: Optional[str]  # آخرین پیام کاربر
    user_feature:Dict[str,Any]
    # userInfo: Optional[Any]  # ایمیل کاربر
    messages: List[Dict[str, str]] # تاریخچه پیام‌ها
    # history_suggestion:List[Dict[Any, Any]]  #تاریخچه سرویس های پیشنهادی
    intents: List[str]  # وضعیت intents شناسایی شده و پارامترها
    # history_intent: List[IntentState]  # وضعیت intents شناسایی شده و پارامترها
    next_node: str

# ---- Manager ----
class ChatStateManager:
    def __init__(self, state: ChatState):
        self.state = state
        if "messages" not in self.state:
            self.state["messages"] = []
        if "intents" not in self.state:
            self.state["intents"] = []

    def add_message(self, role: str, content: str):
        self.state["messages"].append({"role": role, "content": content})
        self.state["input"] = content

    def update_intents(self, new_intents: List[IntentState]):
        for new_intent in new_intents:
            found = False
            for existing in self.state["intents"]:
                if existing["intent"] == new_intent["intent"]:
                    found = True
                    # merge پارامترها: جایگزین null با مقادیر جدید
                    for k, v in new_intent["parameters"].items():
                        if v is not None:
                            existing["parameters"][k] = v
                    # آپدیت status
                    if "status" in new_intent:
                        existing["status"] = new_intent["status"]
                    break
            if not found:
                # intent جدید → اضافه کن
                self.state["intents"].append(new_intent)

    def get_state(self) -> ChatState:
        return self.state