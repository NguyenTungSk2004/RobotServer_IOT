from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from connections import *
from firebase import verify_firebase_token
import gemini
import json

router = APIRouter(prefix="/api/ws")

@router.websocket("/robot/{robot_id}")
async def robot_ws(websocket: WebSocket, robot_id: str):
    await websocket.accept()

    if not register_robot(robot_id, websocket):
        await websocket.close(code=1008, reason=f"Robot {robot_id} đã được kết nối")
        return

    try:
        while True:
            msg = await websocket.receive_text()
            client = get_client(robot_id)
            if client:
                try:
                    response = gemini.generate_robot_response(msg)
                    await client.send_text(response)
                except:
                    unregister_client(client)

    except WebSocketDisconnect:
        unregister_robot(robot_id)
        print(f"Robot {robot_id} disconnected")


@router.websocket("/client/{robot_id}")
async def client_ws(websocket: WebSocket, robot_id: str, token: str):
    if not verify_firebase_token(token):
        return
    
    await websocket.accept()
    
    # Kiểm tra xem có thể điều khiển robot không
    if not register_client(robot_id, websocket):
        if robot_id not in robot_connections:
            reason = f"Robot {robot_id} chưa kết nối"
        else:
            reason = f"Robot {robot_id} đã có client điều khiển"
        
        await websocket.close(code=1008, reason=reason)
        return

    try:
        while True:
            msg = await websocket.receive_text()
            robot = get_robot(robot_id)
            if robot:
                try:
                    actions = gemini.analyze_command(msg)
                    
                    if (len(actions) == 0):
                        await websocket.send_text(json.dumps({
                            "error": "Không phân tích được lệnh",
                            "robot_id": robot_id
                        }))
                        continue

                    for action in actions:
                        message = json.dumps(action)
                        await robot.send_text(message)
                except:
                    await websocket.send_text(json.dumps({
                        "error": "Robot đã ngắt kết nối",
                        "robot_id": robot_id
                    }))
            else:
                await websocket.send_text(json.dumps({
                    "error": "Robot không khả dụng",
                    "robot_id": robot_id
                }))
    except WebSocketDisconnect:
        unregister_client(websocket)
        print(f"Client disconnected from {robot_id}")



