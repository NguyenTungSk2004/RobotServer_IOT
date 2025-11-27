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
    client = None 
    try:
        while True:
            client = get_client(robot_id)
            if not client: continue

            msg = await websocket.receive_text()
            try:
                message_data = json.loads(msg)
                action_id = message_data.get("action_id", "")
                response_message = message_data.get("message", "")

                if not pending_manager.has_pending_actions(robot_id): continue

                next_action = pending_manager.process_robot_completion(robot_id, action_id)

                await client.send_text(json.dumps(response_message, ensure_ascii=False))

                if next_action:
                    await websocket.send_text(json.dumps(next_action.to_dict()))

            except Exception as e:
                await websocket.send_text(f"Lỗi khi xử lý tin nhắn từ robot {robot_id}: {e}")

    except WebSocketDisconnect:
        if client:
            await client.send_text(f"Robot {robot_id} disconnected")
        pending_manager.cancel_robot_actions(robot_id)
        await unregister_robot(robot_id) # Thay đổi này

@router.websocket("/client/{robot_id}")
async def client_ws(websocket: WebSocket, robot_id: str, token: str):
    token_result = verify_firebase_token(token)
    if not token_result['success']:
        await websocket.close(code=1008, reason=f"Invalid token: {token_result.get('error', 'Unknown error')}")
        return
    
    # Kiểm tra xem có thể điều khiển robot không
    if not register_client(robot_id, websocket):
        await websocket.close(code=1008, reason=get_robot_status(robot_id))
        return
    
    await websocket.accept()
    gemini_client = await gemini.get_gemini()
    try:
        robot = get_robot(robot_id)
        await gemini_client.connect()
        while True:
            if not robot:
                await websocket.send_text(json.dumps({
                    "error": "Robot không khả dụng",
                    "robot_id": robot_id
                }, ensure_ascii=False))
                continue

            msg = await websocket.receive_text()

            actions = [] # Khởi tạo actions là một list rỗng
            try:
                message_json = json.loads(msg)
                actions = [message_json]
            except Exception:
                gemini_response = await gemini_client.send_message(msg)
                if gemini_response: # Đảm bảo gemini_response không phải là None
                    actions = gemini_response

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
        if gemini_client: # Chỉ ngắt kết nối nếu gemini_client đã được khởi tạo
            await gemini_client.disconnect()
        pending_manager.cancel_robot_actions(robot_id)
        unregister_client(websocket)
        if robot: # Kiểm tra robot trước khi gửi tin nhắn
            await robot.send_text(f"Client disconnected from {robot_id}")
