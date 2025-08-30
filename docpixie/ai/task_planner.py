"""
Adaptive task planner for DocPixie RAG Agent
Creates and dynamically updates task plans based on agent findings
"""

import json
import uuid
import logging
from typing import List, Optional

from ..models.agent import AgentTask, TaskPlan, TaskResult, TaskStatus
from ..models.document import Document
from ..providers.base import BaseProvider
from ..exceptions import TaskPlanningError
from .prompts import (
    ADAPTIVE_INITIAL_PLANNING_PROMPT,
    ADAPTIVE_PLAN_UPDATE_PROMPT,
    SYSTEM_ADAPTIVE_PLANNER
)

logger = logging.getLogger(__name__)


class TaskPlanner:
    """
    Adaptive task planner that can create and modify task plans based on findings
    Key feature: Agent can add/remove/modify tasks based on what it learns
    """

    def __init__(self, provider: BaseProvider):
        self.provider = provider

    async def create_initial_plan(
        self,
        query: str,
        documents: Optional[List[Document]] = None
    ) -> TaskPlan:
        """
        Create initial task plan from user query with document selection

        Args:
            query: User's question/request
            documents: Available documents (required for document selection)

        Returns:
            TaskPlan with 2-4 initial tasks, each with assigned documents

        Raises:
            TaskPlanningError: If task planning fails
        """
        try:
            logger.info(f"Creating initial task plan for query: {query[:50]}...")

            # Build context about available documents with full summaries
            documents_text = ""
            if documents:
                doc_list = []
                for doc in documents:
                    summary = doc.summary or f"Document with {len(doc.pages)} pages"
                    doc_list.append(f"{doc.id}: {doc.name}\nSummary: {summary}")
                documents_text = "\n\n".join(doc_list)
            else:
                documents_text = "No documents available"

            # Generate initial plan
            prompt = ADAPTIVE_INITIAL_PLANNING_PROMPT.format(
                query=query,
                documents=documents_text
            )

            messages = [
                {"role": "system", "content": SYSTEM_ADAPTIVE_PLANNER},
                {"role": "user", "content": prompt}
            ]

            result = await self.provider.process_text_messages(
                messages=messages,
                max_tokens=500,
                temperature=0.3
            )

            # Parse and create task plan
            task_plan = self._parse_initial_plan(result, query, documents)

            logger.info(f"Created initial plan with {len(task_plan.tasks)} tasks")
            for task in task_plan.tasks:
                logger.debug(f"Task: {task.name} - Document: {task.document}")

            return task_plan

        except Exception as e:
            logger.error(f"Failed to create initial plan: {e}")
            raise TaskPlanningError(f"Failed to create initial task plan: {e}")

    async def update_plan(
        self,
        current_plan: TaskPlan,
        latest_result: TaskResult,
        original_query: str,
        documents: Optional[List[Document]] = None
    ) -> TaskPlan:
        """
        Adaptively update task plan based on latest findings
        This is the key adaptive feature - agent can modify its own plan

        Args:
            current_plan: Current task plan
            latest_result: Result from the task just completed
            original_query: Original user query for context
            documents: Available documents (for new task assignments)

        Returns:
            Updated task plan (may have added/removed/modified tasks)
        """
        result = None
        try:
            logger.info(f"Updating task plan after completing: {latest_result.task.name}")

            # Build current plan status
            plan_status = self._build_plan_status(current_plan)

            # Build progress summary from completed tasks
            progress_summary = self._build_progress_summary(current_plan, latest_result)

            # Build available documents text with full summaries
            available_documents = ""
            if documents:
                doc_list = []
                for doc in documents:
                    summary = doc.summary or f"Document with {len(doc.pages)} pages"
                    doc_list.append(f"{doc.id}: {doc.name}\nSummary: {summary}")
                available_documents = "\n\n".join(doc_list)
            else:
                available_documents = "No documents available"

            # Ask agent to evaluate and update plan
            prompt = ADAPTIVE_PLAN_UPDATE_PROMPT.format(
                original_query=original_query,
                available_documents=available_documents,
                current_plan_status=plan_status,
                completed_task_name=latest_result.task.name,
                task_findings=latest_result.analysis[:500],  # Limit length
                progress_summary=progress_summary
            )

            messages = [
                {"role": "system", "content": SYSTEM_ADAPTIVE_PLANNER},
                {"role": "user", "content": prompt}
            ]

            result = await self.provider.process_text_messages(
                messages=messages,
                max_tokens=500,
                temperature=0.3
            )

            # Apply plan updates
            updated_plan = self._apply_plan_updates(current_plan, result, latest_result)

            logger.info(f"Plan updated - now has {len(updated_plan.tasks)} tasks")
            return updated_plan

        except Exception as e:
            logger.error(f"Failed to update plan: {e}")
            raise TaskPlanningError(f"Failed to update task plan: {e}. \nRaw response: \n{result}")

    def _parse_initial_plan(self, result: str, query: str, documents: Optional[List[Document]] = None) -> TaskPlan:
        """Parse initial planning response and create TaskPlan with document assignments"""
        try:
            plan_data = json.loads(result.strip())
            tasks = []

            # Create map of available document IDs for validation
            valid_doc_ids = set()
            if documents:
                valid_doc_ids = {doc.id for doc in documents}

            for task_data in plan_data.get("tasks", []):
                # Parse and validate single document assignment
                assigned_doc = task_data.get("document", "")
                valid_assigned_doc = assigned_doc if assigned_doc in valid_doc_ids else ""

                task = AgentTask(
                    id=str(uuid.uuid4()),
                    name=task_data.get("name", "Unnamed Task"),
                    description=task_data.get("description", ""),
                    document=valid_assigned_doc,
                    status=TaskStatus.PENDING
                )
                tasks.append(task)

            # Limit to reasonable number of initial tasks
            if len(tasks) > 4:
                tasks = tasks[:4]
                logger.debug("Limited initial tasks to 4")

            return TaskPlan(
                initial_query=query,
                tasks=tasks,
                current_iteration=0
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse initial plan: {e}")
            raise TaskPlanningError(f"Failed to parse task plan JSON: {e}")

    def _apply_plan_updates(
        self,
        current_plan: TaskPlan,
        update_result: str,
        latest_result: TaskResult
    ) -> TaskPlan:
        """Apply updates to the current plan based on agent's decision"""
        try:
            update_data = json.loads(update_result.strip())
            action = update_data.get("action", "continue")
            reason = update_data.get("reason", "No reason provided")

            logger.debug(f"Plan update action: {action} - {reason}")

            if action == "continue":
                # No changes needed
                logger.info("Continuing with current plan unchanged")

            elif action == "add_tasks":
                # Add new tasks
                new_tasks_data = update_data.get("new_tasks", [])
                for task_data in new_tasks_data:
                    assigned_doc = task_data.get("document", "")
                    new_task = AgentTask(
                        name=task_data.get("name", "New Task"),
                        description=task_data.get("description", ""),
                        document=assigned_doc,
                        status=TaskStatus.PENDING
                    )
                    current_plan.add_task(new_task)
                    logger.info(f"Added new task: {new_task.name} - Document: {assigned_doc}")

            elif action == "remove_tasks":
                # Remove specified tasks
                task_ids_to_remove = update_data.get("tasks_to_remove", [])
                for task_id in task_ids_to_remove:
                    if current_plan.remove_task(task_id):
                        logger.info(f"Removed task: {task_id}")

            elif action == "modify_tasks":
                # Modify existing tasks
                modifications = update_data.get("modified_tasks", [])
                for modification in modifications:
                    task_id = modification.get("task_id")
                    task = next((t for t in current_plan.tasks if t.id == task_id), None)
                    if task and task.status == TaskStatus.PENDING:
                        old_name = task.name
                        old_doc = task.document
                        task.name = modification.get("new_name", task.name)
                        task.description = modification.get("new_description", task.description)
                        task.document = modification.get("new_document", task.document)
                        logger.info(f"Modified task '{old_name}' -> '{task.name}' (Document: {old_doc} -> {task.document})")

            current_plan.current_iteration += 1
            return current_plan

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse plan updates: {e}")
            raise TaskPlanningError(f"Failed to parse plan update JSON: {e}")

    def _build_plan_status(self, plan: TaskPlan) -> str:
        """Build text summary of current plan status"""
        status_lines = []
        for task in plan.tasks:
            status_lines.append(f"- {task.name}: {task.status.value}")
        return "\n".join(status_lines)

    def _build_progress_summary(self, plan: TaskPlan, latest_result: TaskResult) -> str:
        """Build summary of progress so far"""
        completed_tasks = plan.get_completed_tasks()

        if not completed_tasks:
            return f"Just completed first task: {latest_result.task.name}"

        summary_parts = []
        for task in completed_tasks:
            summary_parts.append(f"✓ {task.name}")

        return "Completed tasks:\n" + "\n".join(summary_parts)
