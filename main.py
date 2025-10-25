from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ws_routes
import uvicorn
from connections import get_all_robots_status, get_robot_status, is_robot_available

# Model cho request phân tích lệnh
class CommandRequest(BaseModel):
    command: str
    token: str

# Khởi tạo FastAPI app
app = FastAPI(
    title="Robot Server API",
    description="Server để điều khiển robot thông qua WebSocket và REST API",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router
app.include_router(ws_routes.router, tags=["WebSocket"])

@app.get("/", tags=["General"])
async def root():
    """Endpoint chính"""
    return {
        "message": "Robot Server đang chạy",
        "status": "active",
        "endpoints": {
            "robots": "/api/robots",
            "robot_detail": "/api/robots/{robot_id}",
            "websocket_robot": "/api/ws/robot/{robot_id}",
            "websocket_client": "/api/ws/client/{robot_id}",
            "analyze_command": "/api/analyze-command"
        }
    }


@app.get("/api/robots", tags=["Robots"])
async def list_robots(token: str = Query(...)):
    """Lấy danh sách tất cả robot và trạng thái của chúng"""
    robots_status = get_all_robots_status()
    return {
        "robots": robots_status,
        "total": len(robots_status),
        "available": sum(1 for status in robots_status.values() if status == "available"),
        "controlled": sum(1 for status in robots_status.values() if status == "controlled"),
        "disconnected": sum(1 for status in robots_status.values() if status == "disconnected")
    }

@app.get("/api/robots/{robot_id}", tags=["Robots"])
async def get_robot_info(robot_id: str, token: str = Query(...)):
    """Lấy thông tin chi tiết của một robot"""
    status = get_robot_status(robot_id)
    return {
        "robot_id": robot_id,
        "status": status,
        "available_for_control": is_robot_available(robot_id),
        "description": {
            "available": "Robot đã kết nối và sẵn sàng điều khiển",
            "controlled": "Robot đang được điều khiển bởi một client",
            "disconnected": "Robot chưa kết nối hoặc đã ngắt kết nối"
        }.get(status, "Trạng thái không xác định")
    }

if __name__ == "__main__":
    print("Khởi động Robot Server...")
    print("API Documentation: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
