"""
DocPixie Adaptive RAG Agent
Main orchestrator for vision-based document analysis with adaptive task planning
"""

import time
import logging
from typing import List, Optional, Dict, Any

from ..models.agent import (
    ConversationMessage, TaskPlan, TaskResult, QueryResult, TaskStatus
)
from ..models.document import Document, Page
from ..providers.base import BaseProvider
from ..storage.base import BaseStorage
from ..core.config import DocPixieConfig
from ..exceptions import (
    ContextProcessingError, QueryReformulationError, QueryClassificationError,
    TaskPlanningError, PageSelectionError, TaskAnalysisError, ResponseSynthesisError
)
from .context_processor import ContextProcessor
from .query_reformulator import QueryReformulator
from .query_classifier import QueryClassifier
from .task_planner import TaskPlanner
from .page_selector import VisionPageSelector
from .synthesizer import ResponseSynthesizer
from .prompts import TASK_PROCESSING_PROMPT, SYSTEM_DOCPIXIE

logger = logging.getLogger(__name__)


class PixieRAGAgent:
    """
    Adaptive RAG agent with vision-based page selection and dynamic task planning

    Key features:
    - Vision-first page selection (analyzes actual page images)
    - Adaptive task planning (can modify plan based on findings)
    - Single-mode operation (no Flash/Pro distinction)
    - Conversation-aware query processing
    """

    def __init__(
        self,
        provider: BaseProvider,
        storage: BaseStorage,
        config: DocPixieConfig
    ):
        self.provider = provider
        self.storage = storage
        self.config = config

        # Initialize components
        self.context_processor = ContextProcessor(provider, config)
        self.query_reformulator = QueryReformulator(provider)
        self.query_classifier = QueryClassifier(provider)
        self.task_planner = TaskPlanner(provider)
        self.page_selector = VisionPageSelector(provider, config)
        self.synthesizer = ResponseSynthesizer(provider)

        logger.info("Initialized DocPixie RAG Agent")

    def _accumulate_cost(self, total_cost: float) -> float:
        """Accumulate cost from last API call if available"""
        if hasattr(self.provider, 'get_last_cost'):
            last_cost = self.provider.get_last_cost()
            if last_cost is not None:
                return total_cost + last_cost
        return total_cost

    async def process_query(
        self,
        query: str,
        conversation_history: Optional[List[ConversationMessage]] = None,
        task_update_callback: Optional[Any] = None
    ) -> QueryResult:
        """
        Process a user query with adaptive task planning and execution

        Args:
            query: User's question
            conversation_history: Previous conversation context

        Returns:
            QueryResult with comprehensive response and metadata
        """
        start_time = time.time()
        total_cost = 0.0  # Track total cost for this query

        try:
            logger.info(f"Processing query: {query[:100]}...")

            # Step 1: Context Processing (conversation summarization if needed)
            processed_context = ""
            display_messages = conversation_history or []

            if conversation_history:
                processed_context, display_messages = await self.context_processor.process_conversation_context(
                    conversation_history, query
                )
                total_cost = self._accumulate_cost(total_cost)
                logger.info("Processed conversation context")

            # Step 2: Query Reformulation (if conversation context exists)
            reformulated_query = query
            if conversation_history:
                reformulated_query = await self.query_reformulator.reformulate_with_context(
                    query, processed_context
                )
                logger.info(f"Reformulated query: '{query}' → '{reformulated_query}'")

            # Step 3: Query Classification
            classification = await self.query_classifier.classify_query(reformulated_query)
            total_cost = self._accumulate_cost(total_cost)
            logger.info(f"Query classification: {classification['reasoning']}")

            # If query doesn't need documents, return direct answer
            if not classification["needs_documents"]:
                return self._create_direct_answer_result(query, classification["reasoning"], total_cost)

            # Step 4: Get all available documents and pages
            documents = await self.storage.get_all_documents()

            if not documents:
                logger.warning("No documents available for analysis")
                return self._create_no_documents_result(query)

            logger.info(f"Found {len(documents)} documents")

            # Step 5: Task Planning + Document Selection (merged)
            task_plan = await self.task_planner.create_initial_plan(reformulated_query, documents)

            # Report initial task plan
            if task_update_callback:
                await task_update_callback('plan_created', task_plan)

            # Step 6: Execute tasks adaptively
            task_results = await self._execute_adaptive_plan(
                task_plan, reformulated_query, documents, conversation_history, task_update_callback
            )
            
            # Accumulate any costs from task execution
            total_cost = self._accumulate_cost(total_cost)

            # Step 7: Synthesize final response
            final_answer = await self.synthesizer.synthesize_response(reformulated_query, task_results)

            # Step 8: Build final result
            processing_time = time.time() - start_time
            all_selected_pages = []
            for result in task_results:
                all_selected_pages.extend(result.selected_pages)

            result = QueryResult(
                query=query,
                answer=final_answer,
                selected_pages=all_selected_pages,
                task_results=task_results,
                total_iterations=task_plan.current_iteration,
                processing_time_seconds=processing_time,
                total_cost=total_cost  # Always include cost, even if 0
            )

            logger.info(f"Query processed successfully in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            processing_time = time.time() - start_time
            return self._create_error_result(query, str(e), processing_time)

    async def _execute_adaptive_plan(
        self,
        task_plan: TaskPlan,
        original_query: str,
        documents: List[Document],
        conversation_history: Optional[List[ConversationMessage]] = None,
        task_update_callback: Optional[Any] = None
    ) -> List[TaskResult]:
        """Execute task plan with adaptive replanning"""
        task_results = []
        iteration = 0

        while (task_plan.has_pending_tasks() and
               iteration < self.config.max_agent_iterations):

            iteration += 1
            logger.info(f"Agent iteration {iteration}")

            # Get next task to execute
            current_task = task_plan.get_next_pending_task()
            if not current_task:
                break

            logger.info(f"Executing task: {current_task.name}")
            current_task.status = TaskStatus.IN_PROGRESS

            # Report task starting
            if task_update_callback:
                await task_update_callback('task_started', {'task': current_task, 'plan': task_plan})

            # Execute the task
            task_result = await self._execute_single_task(
                current_task, documents, original_query, conversation_history, task_update_callback
            )

            # Mark task completed
            current_task.status = TaskStatus.COMPLETED
            task_results.append(task_result)

            logger.info(f"Task completed: {current_task.name} "
                       f"(analyzed {task_result.pages_analyzed} pages)")

            # Report task completion
            if task_update_callback:
                await task_update_callback('task_completed', {'task': current_task, 'result': task_result, 'plan': task_plan})

            # Update plan adaptively if there are still pending tasks
            if task_plan.has_pending_tasks():
                logger.info("Checking if task plan needs updating...")
                old_task_count = len(task_plan.tasks)
                task_plan = await self.task_planner.update_plan(
                    task_plan, task_result, original_query, documents
                )

                # Report plan update if it changed
                if task_update_callback and len(task_plan.tasks) != old_task_count:
                    await task_update_callback('plan_updated', task_plan)

        task_plan.current_iteration = iteration
        logger.info(f"Task execution completed after {iteration} iterations")
        return task_results

    async def _execute_single_task(
        self,
        task: Any,  # AgentTask
        documents: List[Document],
        original_query: str,
        conversation_history: Optional[List[ConversationMessage]] = None,
        task_update_callback: Optional[Any] = None
    ) -> TaskResult:
        """Execute a single task: document filtering + page selection + analysis"""
        try:
            # Step 1: Filter pages to only the task's assigned document
            task_pages = []
            if task.document:
                # Find the document assigned to this task
                task_doc = next((doc for doc in documents if doc.id == task.document), None)
                if task_doc:
                    task_pages = task_doc.pages
                    logger.info(f"Task {task.name} assigned to document: {task_doc.name} ({len(task_pages)} pages)")
                else:
                    logger.warning(f"Task {task.name} assigned to document {task.document} but document not found")
            else:
                # No specific document assigned - use all pages (fallback)
                task_pages = []
                for doc in documents:
                    task_pages.extend(doc.pages)
                logger.warning(f"Task {task.name} has no document assignment, using all pages")

            # Step 2: Select relevant pages for this task
            selected_pages = await self.page_selector.select_pages_for_task(
                query=task.name,
                query_description=task.description,
                task_pages=task_pages
            )

            logger.info(f"Selected {len(selected_pages)} pages for task: {task.name}")

            # Report page selection
            if task_update_callback:
                page_numbers = [p.page_number for p in selected_pages]
                await task_update_callback('pages_selected', {'task': task, 'page_numbers': page_numbers})

            # Step 3: Analyze selected pages to complete the task
            analysis = await self._analyze_pages_for_task(
                task, selected_pages, original_query, conversation_history
            )

            # Step 4: Create task result
            return TaskResult(
                task=task,
                selected_pages=selected_pages,
                analysis=analysis
            )

        except Exception as e:
            logger.error(f"Failed to execute task {task.name}: {e}")
            # Return result with error message
            return TaskResult(
                task=task,
                selected_pages=[],
                analysis=f"Task execution failed: {e}"
            )

    async def _analyze_pages_for_task(
        self,
        task: Any,  # AgentTask
        pages: List[Page],
        original_query: str,
        conversation_history: Optional[List[ConversationMessage]] = None
    ) -> str:
        """Analyze selected pages to complete a specific task"""
        if not pages:
            return f"No relevant pages found for task: {task.name}"

        try:
            # Build memory summary from conversation if available
            memory_summary = self._build_memory_summary(conversation_history)

            # Create task processing prompt
            prompt = TASK_PROCESSING_PROMPT.format(
                task_description=task.description,
                search_queries=task.description,  # Use task description as query
                memory_summary=memory_summary
            )

            # Build multimodal message with selected page images
            messages = [
                {"role": "system", "content": SYSTEM_DOCPIXIE},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]

            # Add page images to message
            for i, page in enumerate(pages, 1):
                messages[1]["content"].extend([
                    {
                        "type": "image_path",
                        "image_path": page.image_path,
                        "detail": "high"  # Use high detail for task analysis
                    },
                    {
                        "type": "text",
                        "text": f"[Page {i} from document]"
                    }
                ])

            # Process with vision model
            result = await self.provider.process_multimodal_messages(
                messages=messages,
                max_tokens=600,
                temperature=0.3
            )

            return result.strip()

        except Exception as e:
            logger.error(f"Failed to analyze pages for task {task.name}: {e}")
            return f"Page analysis failed for task {task.name}: {e}"

    def _build_memory_summary(
        self,
        conversation_history: Optional[List[ConversationMessage]]
    ) -> str:
        """Build conversation memory summary for context"""
        if not conversation_history or len(conversation_history) == 0:
            return "CONVERSATION CONTEXT: This is the first query in the conversation."

        # Get last few messages for context
        recent_messages = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history

        context_parts = ["CONVERSATION CONTEXT:"]
        for msg in recent_messages:
            role = "User" if msg.role == "user" else "Assistant"
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            context_parts.append(f"- {role}: {content}")

        return "\n".join(context_parts)

    def _create_no_documents_result(self, query: str) -> QueryResult:
        """Create result when no documents are available"""
        return QueryResult(
            query=query,
            answer="I don't have any documents to analyze. Please upload some documents first.",
            selected_pages=[],
            task_results=[],
            total_iterations=0,
            processing_time_seconds=0.0,
            total_cost=0.0  # Always include cost, even if 0
        )

    def _create_error_result(
        self,
        query: str,
        error_message: str,
        processing_time: float
    ) -> QueryResult:
        """Create result when processing fails"""
        return QueryResult(
            query=query,
            answer=f"I encountered an error while processing your query: {error_message}",
            selected_pages=[],
            task_results=[],
            total_iterations=0,
            processing_time_seconds=processing_time,
            total_cost=0.0  # Always include cost, even if 0
        )

    def _create_direct_answer_result(self, query: str, reasoning: str, total_cost: float = 0.0) -> QueryResult:
        """Create result when query doesn't need document analysis"""
        return QueryResult(
            query=query,
            answer=f"This query doesn't require document analysis. {reasoning}",
            selected_pages=[],
            task_results=[],
            total_iterations=0,
            processing_time_seconds=0.0,
            total_cost=total_cost  # Always include cost, even if 0
        )

    async def process_conversation_query(
        self,
        query: str,
        conversation_history: List[ConversationMessage]
    ) -> QueryResult:
        """
        Process a query in conversation context
        This is a convenience method that handles conversation-aware processing
        """
        return await self.process_query(query, conversation_history)

    def get_agent_stats(self) -> Dict[str, Any]:
        """Get agent configuration and statistics"""
        return {
            "provider": self.provider.__class__.__name__,
            "storage": self.storage.__class__.__name__,
            "max_iterations": self.config.max_agent_iterations,
            "max_pages_per_task": self.config.max_pages_per_task,
            "max_tasks_per_plan": self.config.max_tasks_per_plan,
        }
