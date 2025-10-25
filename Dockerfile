# ====== B1: Dùng image Python chính thức ======
FROM python:3.11-slim

# ====== B2: Cài Rust & Cargo (nếu có thư viện cần biên dịch) ======
RUN apt-get update && apt-get install -y rustc cargo

# ====== B3: Cài đặt thư viện Python ======
WORKDIR /app
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ====== B4: Copy toàn bộ source code vào container ======
COPY . .

# ====== B5: Mở cổng cho FastAPI ======
EXPOSE 8000

# ====== B6: Lệnh chạy khi container khởi động ======
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
