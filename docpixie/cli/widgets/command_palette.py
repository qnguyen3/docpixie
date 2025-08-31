"""
Command palette widget for DocPixie CLI
Provides quick access to all commands with filtering and navigation
"""

from typing import List, Dict, Callable, Optional
from textual.widgets import Static, ListView, ListItem, Label
from textual.containers import Container, Vertical
from textual.reactive import reactive
from textual.message import Message
from textual import events
from rich.text import Text


class CommandItem:
    """Represents a single command in the palette"""
    
    def __init__(self, command: str, description: str, handler: Callable = None):
        self.command = command
        self.description = description
        self.handler = handler
    
    def __str__(self) -> str:
        return f"{self.command} - {self.description}"


class CommandPalette(Container):
    """Command palette overlay widget"""
    
    DEFAULT_CSS = """
    CommandPalette {
        display: none;
        layer: overlay;
        dock: bottom;
        offset: 0 -4;  /* Position above input area */
        width: 80;
        height: auto;
        max-height: 15;
        background: $panel;
        border: solid $primary;
        padding: 1;
        align: center bottom;
    }
    
    CommandPalette.visible {
        display: block;
    }
    
    #command-list {
        height: auto;
        max-height: 12;
        scrollbar-background: $panel;
        scrollbar-color: $primary;
    }
    
    .command-item {
        height: 1;
        padding: 0 1;
    }
    
    .command-item.--highlight {
        background: $accent;
        color: $text;
    }
    
    .command-item-selected {
        background: $primary;
        color: $text;
    }
    
    #filter-display {
        background: $surface;
        color: $text;
        height: 1;
        padding: 0 1;
        margin: 0 0 1 0;
    }
    """
    
    # Define all available commands
    COMMANDS = [
        CommandItem("/new", "Start a new conversation (Ctrl+N)"),
        CommandItem("/conversations", "Switch between conversations (Ctrl+L)"),
        CommandItem("/save", "Save current conversation"),
        CommandItem("/clear", "Clear current chat display"),
        CommandItem("/model", "Configure Planning and Vision models (Ctrl+M)"),
        CommandItem("/documents", "Manage and index documents (Ctrl+D)"),
        CommandItem("/help", "Show all available commands"),
        CommandItem("/exit", "Exit the program (Ctrl+Q)"),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filtered_commands: List[CommandItem] = []
        self.selected_index = 0
        self.current_filter = ""
        self.command_items: List[ListItem] = []
    
    def compose(self):
        """Create the command palette UI"""
        with Vertical():
            yield Static("Type to filter commands:", id="filter-display")
            yield ListView(id="command-list")
    
    def on_mount(self):
        """Initialize the command palette"""
        self._update_commands("")
    
    def show(self, filter_text: str = ""):
        """Show the command palette with optional filter"""
        self.current_filter = filter_text
        self._update_commands(filter_text)
        self.add_class("visible")
        
        # Don't focus the ListView - keep focus on input field
        # This allows continued typing while palette is visible
    
    def hide(self):
        """Hide the command palette"""
        self.remove_class("visible")
        self.current_filter = ""
        self.selected_index = 0
    
    def update_filter(self, filter_text: str):
        """Update the command filter"""
        self.current_filter = filter_text
        self._update_commands(filter_text)
        
        # Update filter display
        filter_display = self.query_one("#filter-display", Static)
        if filter_text:
            filter_display.update(f"Filter: {filter_text}")
        else:
            filter_display.update("Type to filter commands:")
    
    def _update_commands(self, filter_text: str):
        """Update the displayed commands based on filter"""
        # Filter commands
        if filter_text:
            self.filtered_commands = [
                cmd for cmd in self.COMMANDS
                if cmd.command.lower().startswith(filter_text.lower())
            ]
        else:
            self.filtered_commands = self.COMMANDS.copy()
        
        # Reset selection
        self.selected_index = 0
        
        # Update ListView
        list_view = self.query_one("#command-list", ListView)
        list_view.clear()
        
        self.command_items = []
        for i, cmd in enumerate(self.filtered_commands):
            # Create rich text for the command item
            command_text = Text()
            command_text.append(cmd.command, style="bold cyan")
            command_text.append(" - ", style="dim")
            command_text.append(cmd.description, style="white")
            
            list_item = ListItem(Static(command_text), classes="command-item")
            list_view.append(list_item)
            self.command_items.append(list_item)
        
        # Highlight first item immediately if available
        if self.command_items and len(self.command_items) > 0:
            # Ensure selected_index is valid
            self.selected_index = 0
            # Force immediate highlight
            self.command_items[0].add_class("command-item-selected")
    
    def _highlight_selected(self):
        """Highlight the currently selected command"""
        # Remove previous highlights
        for item in self.command_items:
            item.remove_class("command-item-selected")
        
        # Highlight current selection
        if 0 <= self.selected_index < len(self.command_items):
            self.command_items[self.selected_index].add_class("command-item-selected")
            
            # Scroll to selected item
            list_view = self.query_one("#command-list", ListView)
            list_view.scroll_to_widget(self.command_items[self.selected_index])
    
    def move_selection_up(self):
        """Move selection up"""
        if self.filtered_commands:
            self.selected_index = max(0, self.selected_index - 1)
            self._highlight_selected()
    
    def move_selection_down(self):
        """Move selection down"""
        if self.filtered_commands:
            self.selected_index = min(len(self.filtered_commands) - 1, self.selected_index + 1)
            self._highlight_selected()
    
    def get_selected_command(self) -> Optional[CommandItem]:
        """Get the currently selected command"""
        if 0 <= self.selected_index < len(self.filtered_commands):
            return self.filtered_commands[self.selected_index]
        return None
    
    def select_current_command(self) -> Optional[str]:
        """Select the current command and return its command string"""
        selected = self.get_selected_command()
        if selected:
            self.hide()
            return selected.command
        return None
    
    # Key handling removed - now handled at app level to maintain input focus


class CommandSelected(Message):
    """Message sent when a command is selected"""
    
    def __init__(self, command: str):
        self.command = command
        super().__init__()


class CommandAutoComplete(Message):
    """Message sent when auto-complete is requested"""
    
    def __init__(self, command: str):
        self.command = command
        super().__init__()