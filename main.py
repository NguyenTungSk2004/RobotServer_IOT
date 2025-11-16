from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from firebase import verify_firebase_token
import ws_routes
import uvicorn
from connections import get_all_robots_status

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
    token_result = verify_firebase_token(token)
    if not token_result['success']:
        raise HTTPException(status_code=401, detail=f"Invalid token: {token_result.get('error', 'Unknown error')}")
    
    robots_status = get_all_robots_status()
    return {
        "robots": robots_status,
        "total": len(robots_status),
        "available": sum(1 for status in robots_status.values() if status == "available"),
        "controlled": sum(1 for status in robots_status.values() if status == "controlled"),
        "disconnected": sum(1 for status in robots_status.values() if status == "disconnected")
    }

if __name__ == "__main__":
    print("Khởi động Robot Server...")
    print("API Documentation: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        # host="127.0.0.1",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
