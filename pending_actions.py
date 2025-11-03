from typing import Dict, List, Optional, Deque, Tuple
from collections import deque
from model import Action

class PendingActionManager:
    def __init__(self):
        # Lưu trữ hàng đợi các PendingAction cho mỗi robot
        self._robot_action_queues: Dict[str, Deque[Action]] = {}
        # Lưu trữ PendingAction hiện tại đang được robot thực thi
        self._robot_current_executing_action: Dict[str, Action] = {}

    def create_action_sequence(self, robot_id: str, actions: List[Action]) -> Optional[Action]:
        """
        Tạo một chuỗi hành động mới cho robot.
        Hủy bỏ chuỗi hành động cũ nếu có.
        Trả về hành động đầu tiên trong chuỗi để gửi đến robot.
        """
        self.cancel_robot_actions(robot_id)

        if not actions:
            return None

        action_queue = deque()
        for action in actions:
            action_queue.append(action)

        self._robot_action_queues[robot_id] = action_queue
        
        # Lấy hành động đầu tiên để gửi đến robot
        first_action: Action = action_queue.popleft()
        self._robot_current_executing_action[robot_id] = first_action
        return first_action

    def process_robot_completion(self, robot_id: str, completed_action_id: str) -> Optional[Tuple[Action, Action]]:
        """
        Xử lý thông báo hoàn thành hành động từ robot.
        Trả về hành động tiếp theo trong chuỗi nếu có.
        """
        current_executing_action = self._robot_current_executing_action.get(robot_id)

        if not current_executing_action or current_executing_action.action_id != completed_action_id:
            return None
        
        self._robot_current_executing_action.pop(robot_id, None)

        action_queue = self._robot_action_queues.get(robot_id)
        if action_queue and len(action_queue) > 0:
            # Lấy hành động tiếp theo từ hàng đợi
            next_action = action_queue.popleft()
            self._robot_current_executing_action[robot_id] = next_action
            return next_action, current_executing_action
        else:
            # Chuỗi hành động đã hoàn thành
            self._robot_action_queues.pop(robot_id, None) # Xóa hàng đợi
            return None
    
    def cancel_robot_actions(self, robot_id: str):
        """Hủy tất cả các hành động đang chờ xử lý và đang thực thi của robot."""
        self._robot_current_executing_action.pop(robot_id, None)
        self._robot_action_queues.pop(robot_id, None)
    
    def has_pending_actions(self, robot_id: str) -> bool:
        """Kiểm tra robot có hành động đang chờ xử lý hoặc đang thực thi không."""
        return robot_id in self._robot_action_queues or robot_id in self._robot_current_executing_action

# Singleton instance
pending_manager = PendingActionManager()
