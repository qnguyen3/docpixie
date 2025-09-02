"""
Task display management for DocPixie CLI
"""

from typing import TYPE_CHECKING, Any
from .state_manager import AppStateManager
from .widgets import ChatArea

if TYPE_CHECKING:
    from .app import DocPixieTUI


class TaskDisplayManager:
    """Manages task plan and progress display in the chat interface"""
    
    def __init__(self, app: 'DocPixieTUI', state_manager: AppStateManager):
        self.app = app
        self.state_manager = state_manager
    
    def display_task_update(self, event_type: str, data: Any) -> None:
        """Display task plan updates"""
        chat_log = self.app.query_one("#chat-log", ChatArea)
        
        if event_type == 'plan_created':
            plan = data
            self.state_manager.current_plan = plan
            self.state_manager.completed_tasks.clear()
            chat_log.hide_processing_status(mark_done=True, final_text="Planning")
            chat_log.show_plan(plan)
        
        elif event_type == 'plan_updated':
            plan = data
            self.state_manager.current_plan = plan
            chat_log.show_plan(plan, is_update=True, completed_tasks=list(self.state_manager.completed_tasks))
        
        elif event_type == 'task_started':
            task = data['task']
            task_name = task.name if hasattr(task, 'name') else str(task)
            
            doc_name = self._get_document_name_for_task(task)
            chat_log.show_task_progress(task_name, None, doc_name)
        
        elif event_type == 'pages_selected':
            task = data['task']
            page_numbers = data.get('page_numbers', [])
            task_name = task.name if hasattr(task, 'name') else str(task)
            
            doc_name = self._get_document_name_for_task(task)
            pages_count = len(page_numbers) if isinstance(page_numbers, (list, tuple)) else 0
            chat_log.show_task_progress(task_name, pages_count, doc_name)
        
        elif event_type == 'task_completed':
            task = data['task']
            task_name = task.name if hasattr(task, 'name') else str(task)
            
            chat_log.update_task_status(task_name, done=True)
            self.state_manager.completed_tasks.add(task_name)
            
            if self.state_manager.current_plan:
                chat_log.show_plan(
                    self.state_manager.current_plan, 
                    is_update=True, 
                    completed_tasks=list(self.state_manager.completed_tasks)
                )
    
    def _get_document_name_for_task(self, task) -> str:
        """Extract document name from task, with fallback to 'document'"""
        doc_name = 'document'
        try:
            task_doc_id = getattr(task, 'document', '')
            if task_doc_id:
                doc = next(
                    (d for d in self.state_manager.indexed_documents if d.id == task_doc_id), 
                    None
                )
                if doc and getattr(doc, 'name', None):
                    doc_name = doc.name
        except Exception:
            pass
        return doc_name