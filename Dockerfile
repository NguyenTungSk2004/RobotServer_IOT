# ====== B1: Stage build code bằng Nuitka ======
FROM python:3.11-slim AS builder

WORKDIR /app

# Cài các công cụ cần thiết
RUN apt-get update && apt-get install -y gcc g++ python3-dev

# Cài thư viện cần thiết và Nuitka để biên dịch
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào container
COPY . .

# Biên dịch file main.py thành file nhị phân (ẩn code)
RUN python -m nuitka --onefile --remove-output main.py

# ====== B2: Image nhỏ, chỉ chứa file đã build ======
FROM python:3.11-slim

WORKDIR /app

# Copy thư viện đã cài sẵn (site-packages)
COPY --from=builder /usr/local/lib/python3.11 /usr/local/lib/python3.11

# Copy file thực thi đã build (main.bin)
COPY --from=builder /app/main.bin /app/main

# Expose port
EXPOSE 8000

# Chạy file đã biên dịch
CMD ["./main"]
