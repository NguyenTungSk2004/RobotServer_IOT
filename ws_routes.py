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
                message_data = json.loads(msg)
                action_id = message_data.get("action_id", "")
                success = message_data.get("success", False)
                response_message = message_data.get("message", "")

                if not pending_manager.has_pending_actions(robot_id): continue

                next_action, current_pending_action_completed = pending_manager.process_robot_completion(robot_id,action_id)

                robot_response = current_pending_action_completed.to_dict()
                robot_response["robot_message"] = response_message
                robot_response["success"] = success

                client = get_client(robot_id)
                if client:
                    robot_response_message = gemini.generate_robot_response(robot_response)
                    await client.send_text(json.dumps(robot_response_message, ensure_ascii=False))

                if next_action:
                    await websocket.send_text(json.dumps(next_action.to_dict()))
                else:
                    # Chuỗi hành động hoàn thành, có thể gửi thông báo cho client nếu cần
                    pass
            except Exception as e:
                await websocket.send_text(f"Lỗi khi xử lý tin nhắn từ robot {robot_id}: {e}")

    except WebSocketDisconnect:
        pending_manager.cancel_robot_actions(robot_id)
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
            
            action_sequence = []
            for action_item in actions:
                action_data = Action(
                    action_id=str(uuid.uuid4()),
                    intent=action_item["intent"],
                    params=action_item["params"],
                )
                action_sequence.append(action_data)
            
            first_action_to_send = pending_manager.create_action_sequence(robot_id, action_sequence)
            
            if first_action_to_send:
                await robot.send_text(json.dumps(first_action_to_send.to_dict()))
            else:
                await websocket.send_text(json.dumps({
                    "error": "Không thể tạo chuỗi hành động",
                    "robot_id": robot_id
                }), ensure_ascii=False)

    except WebSocketDisconnect:
        pending_manager.cancel_robot_actions(robot_id)
        unregister_client(websocket)
        print(f"Client disconnected from {robot_id}")
