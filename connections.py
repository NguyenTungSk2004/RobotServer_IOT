from typing import Dict, Optional
from fastapi import WebSocket

# Lưu các kết nối hiện tại - Quan hệ 1:1 giữa robot và client
robot_connections: Dict[str, WebSocket] = {}
client_connections: Dict[str, WebSocket] = {}
client_to_robot_mapping: Dict[WebSocket, str] = {}  # Ánh xạ ngược từ client websocket đến robot_id

def register_robot(robot_id: str, ws: WebSocket) -> bool:
    """
    Đăng ký robot. Nếu robot đã tồn tại, trả về False
    """
    if robot_id in robot_connections:
        return False  # Robot đã được kết nối
    
    robot_connections[robot_id] = ws
    return True

async def unregister_robot(robot_id: str):
    """
    Hủy đăng ký robot và client đang điều khiển nó
    """
    robot_connections.pop(robot_id, None)
    
    # Hủy client đang điều khiển robot này
    if robot_id in client_connections:
        client_ws = client_connections.pop(robot_id)
        client_to_robot_mapping.pop(client_ws, None)
        try:
            await client_ws.close(code=1000) # Đóng kết nối WebSocket của client
        except RuntimeError:
            # Có thể client đã bị ngắt kết nối
            pass

def register_client(robot_id: str, ws: WebSocket) -> bool:
    """
    Đăng ký client để điều khiển robot. 
    Chỉ cho phép 1 client điều khiển 1 robot.
    Trả về True nếu thành công, False nếu robot đã có client hoặc không tồn tại
    """
    # Kiểm tra robot có tồn tại không
    if robot_id not in robot_connections:
        return False
    
    # Kiểm tra robot đã có client điều khiển chưa
    if robot_id in client_connections:
        return False  # Robot đã có client điều khiển
    
    # Đăng ký client
    client_connections[robot_id] = ws
    client_to_robot_mapping[ws] = robot_id
    return True

def unregister_client(client_ws: WebSocket):
    """
    Hủy đăng ký client
    """
    robot_id = client_to_robot_mapping.pop(client_ws, None)
    if robot_id:
        client_connections.pop(robot_id, None)

def get_robot(robot_id: str) -> Optional[WebSocket]:
    """
    Lấy WebSocket của robot
    """
    return robot_connections.get(robot_id)

def get_client(robot_id: str) -> Optional[WebSocket]:
    """
    Lấy WebSocket của client đang điều khiển robot
    """
    return client_connections.get(robot_id)

def is_robot_available(robot_id: str) -> bool:
    """
    Kiểm tra robot có sẵn để điều khiển không (đã kết nối nhưng chưa có client)
    """
    return robot_id in robot_connections and robot_id not in client_connections

def get_robot_status(robot_id: str) -> str:
    """
    Lấy trạng thái của robot
    """
    if robot_id in client_connections:
        return "controlled"
    else:
        return "available"

def get_all_robots_status() -> Dict[str, str]:
    """
    Lấy trạng thái của tất cả robot
    """
    return {robot_id: get_robot_status(robot_id) for robot_id in robot_connections.keys()}
