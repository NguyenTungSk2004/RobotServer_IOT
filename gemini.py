from dotenv import load_dotenv
from google import genai
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


TEMPLATE_PROMPT_ROBOT_RESPONSE = """
Bạn là robot di chuyển nhận lệnh điều khiển đơn.

Yêu cầu:
- Nếu thực hiện **thành công**, chỉ phản hồi theo mẫu:
  "OK: <tên hành động> đã hoàn thành"
  Ví dụ: "OK: tiến 10m", "OK: rẽ phải 90°", "OK: quay trái 80°"

- Nếu **phát hiện vật cản hoặc lỗi**, phản hồi theo mẫu:
  "ERROR: <mô tả ngắn>"
  Ví dụ: "ERROR: gặp vật cản phía trước", "ERROR: không thể quay trái"

Không cần thêm ký tự đặc biệt, không xuống dòng, không mô tả dài dòng.
"""

def analyze_command(user_command: str):
    full_prompt = TEMPLATE_PROMPT_ANALYZE + user_command

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt
    )

    raw_text = response.text.strip()

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
        return None
     
def generate_robot_response(robot_msg: dict) -> str:
    full_prompt = TEMPLATE_PROMPT_ROBOT_RESPONSE + "\nTrạng thái hiện tại:\n" + json.dumps(robot_msg, ensure_ascii=False, indent=2)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_prompt
    )

    return response.text

