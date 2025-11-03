import asyncio
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from connections import *
from firebase import verify_firebase_token
import gemini
import json
from model import Action
from pending_actions import pending_manager

router = APIRouter(prefix="/api/ws")

@router.websocket("/robot/{robot_id}")
async def robot_ws(websocket: WebSocket, robot_id: str):
    if not register_robot(robot_id, websocket):
        await websocket.close(code=1008, reason=f"Robot {robot_id} đã được kết nối")
        return

    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                if pending_manager.has_pending_action(robot_id):
                    message = json.loads(msg)
                    pending_manager.resolve_action(
                        robot_id, 
                        message.get("action_id", ""), 
                        message.get("success", False),
                        message.get("message", "")
                    )
            except Exception as e:
                await websocket.send_text(f"Lỗi khi xử lý tin nhắn từ robot {robot_id}: {e}")

    except WebSocketDisconnect:
        pending_manager.cleanup_robot(robot_id)
        unregister_robot(robot_id)
        print(f"Robot {robot_id} disconnected")

@router.websocket("/client/{robot_id}")
async def client_ws(websocket: WebSocket, robot_id: str, token: str):
    if not verify_firebase_token(token):
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    # Kiểm tra xem có thể điều khiển robot không
    if not register_client(robot_id, websocket):
        await websocket.close(code=1008, reason=get_robot_status(robot_id))
        return
    
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_text()
            robot = get_robot(robot_id)
            if not robot:
                await websocket.send_text(json.dumps({
                    "error": "Robot không khả dụng",
                    "robot_id": robot_id
                }), ensure_ascii=False)
                continue 

            actions = gemini.analyze_command(msg)
            
            if (len(actions) == 0):
                await websocket.send_text(json.dumps({
                    "error": "Không phân tích được lệnh",
                    "robot_id": robot_id
                }, ensure_ascii=False))
                continue
            
            for action in actions:
                action_data = Action(
                    action_id=str(uuid.uuid4()),
                    intent=action["intent"],
                    params=action["params"]
                )
                message = pending_manager.create_action(robot_id, action_data)
                await robot.send_text(json.dumps(message.data.to_dict()))

                result = await asyncio.wait_for(message.future, timeout=None)
                response = gemini.generate_robot_response(result)
                await websocket.send_text(response)

    except WebSocketDisconnect:
        pending_manager.cleanup_robot(robot_id)
        unregister_client(websocket)
        print(f"Client disconnected from {robot_id}")
