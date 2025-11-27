import asyncio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from websockets.exceptions import ConnectionClosedError 
import os 
import json

load_dotenv()
API_KEY = os.getenv("API_GEMINI_KEY")
client = genai.Client(api_key=API_KEY)

TEMPLATE_PROMPT_ANALYZE = """
Bạn là một AI chuyên phân tích **ý định di chuyển** của người dùng.
Nhiệm vụ của bạn là đọc câu lệnh và **trả về JSON hợp lệ** mô tả chuỗi hành động theo đúng thứ tự mà người dùng nói ra.

### Cấu trúc JSON:
{
  "actions": [
    {
      "intent": "<một trong: tien, lui, re_trai, re_phai, dung_lai, nang, ha>",
      "params": {
        "<tên_tham_số>": <giá_trị>,
        "unit": "<đơn_vị_nếu_có>"
      }
    },
    ...
  ]
}

### Quy tắc nhận dạng:

- **Thứ tự xuất hiện:** giữ nguyên thứ tự các hành động theo cách người dùng nói.
- **Không bỏ hành động lặp lại.**
- Nếu hành động không có tham số → "params": {}.
- Nếu có số và đơn vị (vd: “2 mét”, “90 độ”) → tách thành:
  - "distance": 2, "unit": "m"
  - "angle": 90, "unit": "deg"

### Quy tắc ngữ nghĩa:

1. **Hành động di chuyển:**
   - "đi thẳng", "tiến tới", "tiến lên" → intent: `"tien"`
   - "lùi", "quay lại", "đi lùi" → intent: `"lui"`
    - "dừng lại", "ngừng", "dừng" → intent: `"dung_lai"`

2. **Hành động rẽ (chỉ xoay hướng nhìn, không di chuyển):**
   - "rẽ trái" → intent: `"re_trai"`
   - "rẽ phải" → intent: `"re_phai"`
   - Nếu không có thông tin góc trong "rẽ trái/phải" → mặc định `"angle": 90, "unit": "deg"`.

3. **Hành động nâng/hạ:**
   - "nâng", "nâng lên" → intent: `"nang"`
   - "hạ", "hạ xuống" → intent: `"ha"`

4. Chỉ trả JSON hợp lệ, không thêm giải thích.

---

### Ví dụ:
Input:
"Đi thẳng 5 mét rẽ trái rồi tiến lên 2 mét nữa"

Output:
{
  "actions": [
    { "intent": "tien", "params": { "distance": 5, "unit": "m" } },
    { "intent": "re_trai", "params": { "angle": 90, "unit": "deg" } },
    { "intent": "tien", "params": { "distance": 2, "unit": "m" } }
  ]
}

---

Input:
"Quay phải 45 độ rồi đi thẳng 3 mét"

Output:
{
  "actions": [
    { "intent": "re_phai", "params": { "angle": 45, "unit": "deg" } },
    { "intent": "tien", "params": { "distance": 3, "unit": "m" } }
  ]
}

Phân tích câu lệnh sau:

"""

def normalize_response(response: str):
    raw_text = response.strip()

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.lower().startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        data = json.loads(raw_text)
        return data["actions"]
    except json.JSONDecodeError as e:
        print("JSON parse error:", e)
        print("Raw text:", raw_text)
        return []

class GeminiLiveClient:
    """
    Lớp quản lý phiên Live API của Gemini.
    """
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-live-001"):
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.session = None
        self.is_connected = False
        self._connector = None 
        self.prompt_template_sent = False

    async def connect(self):
        if self.is_connected:
            print("Kết nối Gemini Live đã được thiết lập.")
            return

        try:
            self._connector = self.client.aio.live.connect( 
                model=self.model,
                config=types.LiveConnectConfig(response_modalities=["TEXT"]),
            )
            self.session = await self._connector.__aenter__()
            self.is_connected = True
            print("Kết nối Gemini Live thành công.")
        except Exception as e:
            self.is_connected = False
            self._connector = None # Đảm bảo connector được reset
            print(f"Lỗi kết nối Gemini Live: {e}")
            raise 

    async def disconnect(self):
        if not self.is_connected or not self.session or not self._connector:
            return

        try:
            await self._connector.__aexit__(None, None, None)
            self.is_connected = False
            self.session = None
            self._connector = None
            print("Đã đóng kết nối Gemini Live.")
        except Exception as e:
            print(f"Lỗi khi đóng kết nối Gemini Live: {e}")

    async def send_message(self, user_text: str) -> list:
        if not self.session or not self.is_connected:
            raise ConnectionError("Không có kết nối Gemini Live. Vui lòng gọi connect() trước.")
        
        full_response = ""
        parts_to_send = []

        if not self.prompt_template_sent:
            parts_to_send.append(types.Part(text=TEMPLATE_PROMPT_ANALYZE))
            self.prompt_template_sent = True
        parts_to_send.append(types.Part(text=user_text))

        try:
            await self.session.send_client_content(
                turns=types.Content(
                    role="user", 
                    parts=parts_to_send
                )
            )
        except Exception as e:
            print(f"Lỗi khi gửi nội dung đến Gemini Live: {e}")
            raise

        try:
            async for message in self.session.receive():
                if message.server_content:
                    server_content = message.server_content
                    
                    if server_content.model_turn and server_content.model_turn.parts:
                        for part in server_content.model_turn.parts:
                            if part.text:
                                full_response += part.text
                                
                    if server_content.turn_complete:
                      return normalize_response(full_response)
                      
        except ConnectionClosedError as e:
            await self.disconnect()
            raise ConnectionError(f"Kết nối Gemini Live bị đóng trong khi nhận tin nhắn: {e}")

async def get_gemini():
    client = GeminiLiveClient(api_key=API_KEY)
    return client