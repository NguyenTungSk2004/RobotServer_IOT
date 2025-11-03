import asyncio
import time
from typing import Dict
from model import Action, PendingAction

class PendingActionManager:
    def __init__(self):
        self._robot_current_action: Dict[str, PendingAction] = {}
    
    def create_action(self, robot_id: str, action_data: Action) -> PendingAction:
        """Tạo action mới cho robot (hủy action cũ nếu có)"""
        self.cancel_robot_action(robot_id, "new_action_started")
        
        # Tạo action mới
        future = asyncio.get_event_loop().create_future()
        
        action = PendingAction(
            data=action_data,
            future=future,
            created_at=time.time(),
        )
        
        # Lưu action hiện tại
        self._robot_current_action[robot_id] = action
        
        return action

    def resolve_action(self, robot_id: str, action_id: str, action_status: bool, message: str) -> bool:
        current_action = self._robot_current_action.get(robot_id)
        
        if not current_action or current_action.data.action_id != action_id:
            return False
        
        if current_action.future.done():
            return False
        
        # Prepare result with action info and success status
        result = {
            'action_id': current_action.data.action_id,
            'intent': current_action.data.intent,
            'params': current_action.data.params,
            'created_at': current_action.created_at,
            'success': action_status,
            'message': message
        }
        
        # Resolve future
        current_action.future.set_result(result)
        
        # Cleanup
        self._robot_current_action.pop(robot_id, None)
        
        return True
    
    def cancel_robot_action(self, robot_id: str, reason: str = "cancelled"):
        """Hủy action hiện tại của robot"""
        current_action = self._robot_current_action.pop(robot_id, None)
        
        if current_action and not current_action.future.done():
            current_action.future.set_exception(Exception(f"Action cancelled: {reason}"))
    
    def has_pending_action(self, robot_id: str) -> bool:
        """Kiểm tra robot có action đang pending không"""
        return robot_id in self._robot_current_action
    
    def cleanup_robot(self, robot_id: str):
        """Cleanup tất cả data của robot khi disconnect"""
        self.cancel_robot_action(robot_id, "robot_disconnected")

# Singleton instance
pending_manager = PendingActionManager()
