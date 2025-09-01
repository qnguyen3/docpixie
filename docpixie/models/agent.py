"""
Agent models and data structures for DocPixie RAG Agent
"""

import uuid
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum
from datetime import datetime

from .document import Page


class TaskStatus(str, Enum):
    """Agent task status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class ConversationMessage:
    """Represents a single conversation message"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    cost: float = 0.0  # Cost for this message (agent pipeline total for assistant messages)

    def __post_init__(self):
        """Validate message data"""
        if self.role not in ["system", "user", "assistant"]:
            raise ValueError("Role must be 'user' or 'assistant'")
        if not self.content.strip():
            raise ValueError("Content cannot be empty")


@dataclass
class AgentTask:
    """Represents a single task in the agent's plan"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    document: str = ""  # Single document ID assigned to this task

    def __post_init__(self):
        """Validate task data"""
        if not self.name.strip():
            raise ValueError("Task name cannot be empty")
        if not self.description.strip():
            raise ValueError("Task description cannot be empty")


@dataclass
class TaskPlan:
    """Represents the agent's current task plan"""
    initial_query: str
    tasks: List[AgentTask] = field(default_factory=list)
    current_iteration: int = 0

    def get_next_pending_task(self) -> Optional[AgentTask]:
        """Get the next task that needs to be executed"""
        return next((task for task in self.tasks if task.status == TaskStatus.PENDING), None)

    def has_pending_tasks(self) -> bool:
        """Check if there are any pending tasks"""
        return any(task.status == TaskStatus.PENDING for task in self.tasks)

    def mark_task_completed(self, task_id: str) -> bool:
        """Mark a task as completed"""
        task = next((t for t in self.tasks if t.id == task_id), None)
        if task:
            task.status = TaskStatus.COMPLETED
            return True
        return False

    def add_task(self, task: AgentTask):
        """Add a new task to the plan"""
        self.tasks.append(task)

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the plan"""
        original_length = len(self.tasks)
        self.tasks = [t for t in self.tasks if t.id != task_id]
        return len(self.tasks) < original_length

    def get_completed_tasks(self) -> List[AgentTask]:
        """Get all completed tasks"""
        return [task for task in self.tasks if task.status == TaskStatus.COMPLETED]


@dataclass
class TaskResult:
    """Represents the result of executing a single task"""
    task: AgentTask
    selected_pages: List[Page]
    analysis: str
    pages_analyzed: int = 0

    def __post_init__(self):
        """Calculate pages analyzed"""
        self.pages_analyzed = len(self.selected_pages)


@dataclass
class AgentQueryResult:
    """Represents the final result of processing a user query through the agent pipeline"""
    query: str
    answer: str
    selected_pages: List[Page]
    task_results: List[TaskResult] = field(default_factory=list)
    total_iterations: int = 0
    processing_time_seconds: float = 0.0
    total_cost: float = 0.0  # Total cost of all API calls for this query

    def get_unique_pages(self) -> List[Page]:
        """Get unique pages from all task results"""
        seen_paths = set()
        unique_pages = []

        for page in self.selected_pages:
            if page.image_path not in seen_paths:
                seen_paths.add(page.image_path)
                unique_pages.append(page)

        return unique_pages

    def get_total_pages_analyzed(self) -> int:
        """Get total number of pages analyzed across all tasks"""
        return sum(result.pages_analyzed for result in self.task_results)
