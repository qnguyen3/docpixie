"""
Reactive ChatArea widget for DocPixie CLI
Replaces RichLog with reactive status updates and content management
"""

import asyncio
import random
from typing import List, Dict, Optional, Any
from textual.widgets import Static
from textual.containers import Container, Vertical, ScrollableContainer
from textual.timer import Timer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text


class ChatArea(ScrollableContainer):
    """
    Reactive chat area widget that can update specific content parts
    instead of just appending like RichLog
    """

    DEFAULT_CSS = """
    ChatArea {
        height: 1fr;
        scrollbar-background: #2d1f2d;
        scrollbar-color: #ff99cc;
        scrollbar-size: 1 1;
    }

    ChatArea > Vertical {
        height: auto;
        min-height: 100%;
        padding: 1;
    }
    """

    STATUS_VERBS = [
        "planning", "cooking", "brewing", "analyzing",
        "vibing", "grinding", "scheming", "processing",
        "thinking", "computing", "flexing", "scheming",
        "hustling",
    ]

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.content_container = Vertical()

        self.message_widgets: List[Static] = []
        self.current_processing_widget: Optional[Static] = None
        self.current_plan_widget: Optional[Static] = None
        self.task_widgets: Dict[str, Static] = {}

        self.processing_timer: Optional[Timer] = None
        self.spinner_tasks: Dict[str, asyncio.Task] = {}
        self.current_verb_index = 0

        self.can_focus = True

    def compose(self):
        """Create the chat area layout"""
        yield self.content_container

    async def on_unmount(self):
        """Clean up tasks when widget is unmounted"""
        self._stop_all_animations()

    def add_user_message(self, content: str):
        """Add a user message to the chat"""
        user_md = Markdown(content)
        user_panel = Panel(user_md, border_style="green", expand=True, padding=(0, 1))
        widget = Static(user_panel)

        self.content_container.mount(widget)
        self.message_widgets.append(widget)

        self._scroll_to_latest()

    def add_assistant_message(self, content: str):
        """Add an assistant message to the chat"""
        md = Markdown(content)
        assistant_panel = Panel(md, border_style="blue", expand=True, padding=(0, 1))
        widget = Static(assistant_panel)

        self.content_container.mount(widget)
        self.message_widgets.append(widget)

        self._scroll_to_latest()

    def add_static_text(self, content: str, classes: str = ""):
        """Add static text content"""
        widget = Static(content, classes=classes)
        self.content_container.mount(widget)
        self.message_widgets.append(widget)
        self._scroll_to_latest()

    def show_processing_status(self):
        """Show processing status with spinner and rotating text"""
        if self.current_processing_widget:
            self.hide_processing_status()

        # Create processing widget
        self.current_processing_widget = Static("", classes="task-update")
        self.content_container.mount(self.current_processing_widget)
        self.message_widgets.append(self.current_processing_widget)
        self._scroll_to_latest()

        self._start_processing_animation()

    def hide_processing_status(self, mark_done: bool = False, final_text: str = "Planning"):
        """Hide processing status and optionally mark as done"""
        if self.current_processing_widget:
            if mark_done:
                # Show final done status
                done_text = Text()
                done_text.append("● ", style="green bold")
                done_text.append(f"Done({final_text})", style="green")
                self.current_processing_widget.update(done_text)

            self._stop_processing_animation()

            if not mark_done:
                # Remove widget if not marking as done
                try:
                    self.current_processing_widget.remove()
                except:
                    pass

            self.current_processing_widget = None

    def show_plan(self, plan_data: Any, is_update: bool = False, completed_tasks: Optional[List[str]] = None):
        """Show plan as a todo list"""
        # Create plan content
        plan_text = Text()
        plan_text.append("Task Plan:\n", style="yellow bold")

        if hasattr(plan_data, 'tasks'):
            tasks = plan_data.tasks
        elif isinstance(plan_data, list):
            tasks = plan_data
        else:
            tasks = []

        for i, task in enumerate(tasks, 1):
            task_name = task.name if hasattr(task, 'name') else str(task)

            # Check if task is completed
            is_completed = completed_tasks and task_name in completed_tasks

            if is_completed:
                # Green strikethrough for completed tasks
                plan_text.append(f"  {i}. ", style="dim")
                plan_text.append(task_name, style="green strike")
                plan_text.append("\n")
            else:
                # Normal for incomplete tasks
                plan_text.append(f"  {i}. {task_name}\n", style="white")

        if is_update and self.current_plan_widget:
            # Update existing plan widget content instead of removing/recreating
            self.current_plan_widget.update(plan_text)
        else:
            # Create new plan widget
            self.current_plan_widget = Static(plan_text, classes="task-update")
            self.content_container.mount(self.current_plan_widget)
            self.message_widgets.append(self.current_plan_widget)

        self._scroll_to_latest()

    def show_task_progress(self, task_name: str, pages_count: Optional[int], doc_name: str):
        """Show task progress with spinner.
        If pages_count is None or <= 0, show a generic verb (planning/cooking/...)
        until we have the actual pages count.
        """
        task_id = f"task_{task_name}"

        # Remove existing task widget if exists
        if task_id in self.task_widgets:
            try:
                self.task_widgets[task_id].remove()
            except:
                pass

        # Create task widget
        task_widget = Static("", classes="task-update")

        # Insert task widget right after the plan widget, not at the end
        if self.current_plan_widget and self.current_plan_widget in self.content_container.children:
            plan_index = list(self.content_container.children).index(self.current_plan_widget)
            # Find the position after all existing task widgets following the plan
            insert_index = plan_index + 1
            for existing_task_widget in self.task_widgets.values():
                if existing_task_widget in self.content_container.children:
                    existing_index = list(self.content_container.children).index(existing_task_widget)
                    if existing_index >= insert_index:
                        insert_index = existing_index + 1

            # Mount at specific position
            if insert_index < len(self.content_container.children):
                # Insert at specific position
                self.content_container.mount(task_widget, before=self.content_container.children[insert_index])
            else:
                # Add at the end if insert_index is at the end
                self.content_container.mount(task_widget)
        else:
            # Fallback: mount at the end
            self.content_container.mount(task_widget)

        self.task_widgets[task_id] = task_widget
        self.message_widgets.append(task_widget)
        self._scroll_to_latest()

        # Start spinner animation for this task
        preparing = (pages_count is None) or (isinstance(pages_count, int) and pages_count <= 0)
        self._start_task_animation(task_id, task_name, pages_count or 0, doc_name, preparing=preparing)

    def update_task_status(self, task_name: str, done: bool = False):
        """Update task status and mark as done if needed"""
        task_id = f"task_{task_name}"

        if task_id in self.task_widgets:
            if done:
                # Stop animation and mark as done
                if task_id in self.spinner_tasks:
                    try:
                        task = self.spinner_tasks[task_id]
                        if not task.done():
                            task.cancel()
                    except Exception:
                        pass
                    del self.spinner_tasks[task_id]

                # Update to done status
                done_text = Text()
                done_text.append("● ", style="green bold")
                done_text.append(f"Done({task_name})", style="green")
                self.task_widgets[task_id].update(done_text)

    def clear(self):
        """Clear all content"""
        # Stop all animations
        self._stop_all_animations()

        # Clear container
        try:
            self.content_container.remove_children()
        except:
            pass

        # Reset tracking
        self.message_widgets.clear()
        self.task_widgets.clear()
        self.current_processing_widget = None
        self.current_plan_widget = None

    def _scroll_to_latest(self):
        """Scroll to the bottom to show latest content"""
        # Schedule scroll after next refresh to ensure content is rendered
        def scroll_to_bottom():
            try:
                self.scroll_end()
            except:
                # Try alternative scrolling methods
                try:
                    if self.message_widgets:
                        last_widget = self.message_widgets[-1]
                        self.scroll_to_widget(last_widget, animate=False)
                except:
                    pass

        try:
            self.call_after_refresh(scroll_to_bottom)
        except:
            # Direct scroll as fallback
            scroll_to_bottom()

    def _start_processing_animation(self):
        """Start processing animation with rotating text"""
        if not self.current_processing_widget:
            return

        async def animate_processing():
            spinner_index = 0
            verb_timer = 0

            while self.current_processing_widget:
                try:
                    spinner = self.SPINNER_FRAMES[spinner_index % len(self.SPINNER_FRAMES)]
                    spinner_index += 1

                    # Update status text every 2 seconds (20 iterations at 0.1s each)
                    if verb_timer % 20 == 0:
                        self.current_verb_index = random.randint(0, len(self.STATUS_VERBS) - 1)

                    current_verb = self.STATUS_VERBS[self.current_verb_index]

                    # Create display text
                    display_text = Text()
                    display_text.append(f"{spinner} ", style="bold #ff99cc")
                    display_text.append(f"{current_verb.capitalize()}...", style="#ff99cc")

                    self.current_processing_widget.update(display_text)
                    verb_timer += 1

                    await asyncio.sleep(0.1)

                except Exception:
                    break

        task = asyncio.create_task(animate_processing())
        self.spinner_tasks["processing"] = task

    def _start_task_animation(self, task_id: str, task_name: str, pages_count: int, doc_name: str, preparing: bool = False):
        """Start spinner animation for a specific task.
        When preparing=True, show rotating verbs until page count is known.
        """
        task_widget = self.task_widgets.get(task_id)
        if not task_widget:
            return

        async def animate_task():
            spinner_index = 0
            verb_timer = 0
            verb_index = random.randint(0, len(self.STATUS_VERBS) - 1) if preparing else 0

            while task_id in self.task_widgets:
                try:
                    spinner = self.SPINNER_FRAMES[spinner_index % len(self.SPINNER_FRAMES)]
                    spinner_index += 1

                    display_text = Text()
                    display_text.append(f"{spinner} ", style="bold #ff99cc")

                    if preparing:
                        # Rotate status verb every ~2 seconds
                        if verb_timer % 20 == 0:
                            verb_index = random.randint(0, len(self.STATUS_VERBS) - 1)
                        current_verb = self.STATUS_VERBS[verb_index]
                        display_text.append(f"{current_verb.capitalize()}...", style="#ff99cc")
                        verb_timer += 1
                    else:
                        # Use proper pluralization when analyzing
                        unit = "page" if pages_count == 1 else "pages"
                        display_text.append(f"Analyzing {pages_count} {unit} in {doc_name}", style="#ff99cc")

                    task_widget.update(display_text)
                    await asyncio.sleep(0.1)

                except Exception:
                    break

        task = asyncio.create_task(animate_task())
        self.spinner_tasks[task_id] = task

    def _stop_processing_animation(self):
        """Stop processing animation"""
        if "processing" in self.spinner_tasks:
            try:
                task = self.spinner_tasks["processing"]
                if not task.done():
                    task.cancel()
            except Exception:
                pass
            del self.spinner_tasks["processing"]

    def _stop_all_animations(self):
        """Stop all animation tasks"""
        for task in self.spinner_tasks.values():
            try:
                if not task.done():
                    task.cancel()
            except Exception:
                pass
        self.spinner_tasks.clear()

    def write(self, content):
        """Compatibility method for RichLog replacement"""
        if isinstance(content, (Panel, Markdown)):
            widget = Static(content)
            self.content_container.mount(widget)
            self.message_widgets.append(widget)
        else:
            widget = Static(str(content))
            self.content_container.mount(widget)
            self.message_widgets.append(widget)

        self._scroll_to_latest()
