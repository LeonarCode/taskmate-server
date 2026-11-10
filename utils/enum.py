from enum import Enum

class UserType(str, Enum):
    EMPLOYEE = "employee"
    STUDENT = "student"

class Colors(str, Enum):
    PURPLE = "0xFF7C3AED"
    MAGENTA = "0xFFEC4899"
    GREEN = "0xFF22C55E"
    AMBER = "0xFFF59E0B"
    RED = "0xFFEF4444"
    BLUE = "0xFF3B82F6"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    TASK_REF = "task_ref"
    SYSTEM_MESSAGE = "system_message"

class NotifType(str, Enum):
    MESSAGE = "message"
    TASK_DEADLINE = "task_deadline"
    SERVER_ACTIVITY = "server_activity"
    TASK_REMINDER = "task_reminder"
    