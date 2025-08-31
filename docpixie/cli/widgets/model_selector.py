"""
Model selector dialog for DocPixie CLI
Allows users to switch between Planning and Vision models
"""

from typing import Optional
from textual.widgets import Static, ListView, ListItem, Label, Button, TabbedContent, TabPane
from textual.containers import Container, Vertical, Horizontal
from textual.screen import ModalScreen
from textual.message import Message
from textual import events

from ..config import get_config_manager, PLANNING_MODELS, VISION_MODELS


class ModelSelected(Message):
    """Message sent when models are selected"""
    
    def __init__(self, text_model: str, vision_model: str):
        self.text_model = text_model
        self.vision_model = vision_model
        super().__init__()


class ModelSelectorDialog(ModalScreen):
    """Modal dialog for selecting AI models"""
    
    CSS = """
    ModelSelectorDialog {
        align: center middle;
    }
    
    #dialog-container {
        width: 80;
        height: 38;
        padding: 1;
        background: $surface;
        border: solid $primary;
    }
    
    .title {
        height: 1;
        margin: 0 0 1 0;
    }
    
    #model-tabs {
        height: 28;
        margin: 0;
    }
    
    #planning-list, #vision-list {
        height: 20;
        scrollbar-background: $panel;
        scrollbar-color: $primary;
        scrollbar-size: 1 1;
        border: solid $accent;
        padding: 1;
        margin: 0;
    }
    
    .model-item {
        height: auto;
        padding: 0 1;
        margin: 0;
    }
    
    .model-item-selected {
        background: $primary;
        color: $text;
        text-style: bold;
    }
    
    .model-item-current {
        background: $success 30%;
        border-left: thick $success;
    }
    
    #button-container {
        align: center middle;
        margin-top: 1;
    }
    
    .tab-info {
        color: $text-muted;
        margin: 0;
        height: 1;
    }
    
    #current-selection {
        height: 1;
        margin: 1 0;
    }
    
    TabbedContent {
        height: 100%;
    }
    
    TabPane {
        padding: 1;
    }
    """
    
    def __init__(self):
        super().__init__()
        self.config_manager = get_config_manager()
        self.current_text_model = self.config_manager.config.text_model
        self.current_vision_model = self.config_manager.config.vision_model
        self.selected_text_model = self.current_text_model
        self.selected_vision_model = self.current_vision_model
        self.planning_items = []
        self.vision_items = []
        self.planning_selected_index = 0
        self.vision_selected_index = 0
        self.active_tab = "planning"  # Track which tab is active
    
    def compose(self):
        """Create the model selector dialog"""
        with Container(id="dialog-container"):
            yield Static("[bold]🤖 Model Configuration[/bold]", classes="title")
            
            with TabbedContent(id="model-tabs"):
                with TabPane("Planning Model", id="planning-tab"):
                    yield Static(
                        "Select model for planning and text:",
                        classes="tab-info"
                    )
                    yield ListView(id="planning-list")
                
                with TabPane("Vision Model", id="vision-tab"):
                    yield Static(
                        "Select model for vision and images:",
                        classes="tab-info"
                    )
                    yield ListView(id="vision-list")
            
            # Current selection display
            yield Static(id="current-selection", classes="info")
            
            # Action buttons
            with Horizontal(id="button-container"):
                yield Button("Save Changes", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")
    
    def on_mount(self):
        """Load models when dialog mounts"""
        self._load_planning_models()
        self._load_vision_models()
        self._update_selection_display()
    
    def _load_planning_models(self):
        """Load and display planning models"""
        list_view = self.query_one("#planning-list", ListView)
        list_view.clear()
        self.planning_items = []
        
        for i, model in enumerate(PLANNING_MODELS):
            # Create model item with indicator for current model
            if model == self.current_text_model:
                model_display = f"[green bold]✓[/green bold] [bold]{model}[/bold] [dim](current)[/dim]"
            else:
                model_display = f"  {model}"
            
            list_item = ListItem(Label(model_display), classes="model-item")
            
            # Mark current model
            if model == self.current_text_model:
                list_item.add_class("model-item-current")
                self.planning_selected_index = i
            
            list_view.append(list_item)
            self.planning_items.append(list_item)
        
        # Highlight selected
        if self.planning_items:
            self.planning_items[self.planning_selected_index].add_class("model-item-selected")
    
    def _load_vision_models(self):
        """Load and display vision models"""
        list_view = self.query_one("#vision-list", ListView)
        list_view.clear()
        self.vision_items = []
        
        for i, model in enumerate(VISION_MODELS):
            # Create model item with indicator for current model
            if model == self.current_vision_model:
                model_display = f"[green bold]✓[/green bold] [bold]{model}[/bold] [dim](current)[/dim]"
            else:
                model_display = f"  {model}"
            
            list_item = ListItem(Label(model_display), classes="model-item")
            
            # Mark current model
            if model == self.current_vision_model:
                list_item.add_class("model-item-current")
                self.vision_selected_index = i
            
            list_view.append(list_item)
            self.vision_items.append(list_item)
        
        # Highlight selected
        if self.vision_items:
            self.vision_items[self.vision_selected_index].add_class("model-item-selected")
    
    def _update_selection_display(self):
        """Update the current selection display"""
        selection_display = self.query_one("#current-selection", Static)
        display_text = f"[dim]Planning:[/dim] [cyan]{self.selected_text_model}[/cyan] [dim]|[/dim] [dim]Vision:[/dim] [magenta]{self.selected_vision_model}[/magenta]"
        selection_display.update(display_text)
    
    def _highlight_planning_selected(self):
        """Highlight the selected planning model"""
        for item in self.planning_items:
            item.remove_class("model-item-selected")
        
        if 0 <= self.planning_selected_index < len(self.planning_items):
            self.planning_items[self.planning_selected_index].add_class("model-item-selected")
            self.selected_text_model = PLANNING_MODELS[self.planning_selected_index]
            
            # Scroll to selected
            list_view = self.query_one("#planning-list", ListView)
            list_view.scroll_to_widget(self.planning_items[self.planning_selected_index])
            
            self._update_selection_display()
    
    def _highlight_vision_selected(self):
        """Highlight the selected vision model"""
        for item in self.vision_items:
            item.remove_class("model-item-selected")
        
        if 0 <= self.vision_selected_index < len(self.vision_items):
            self.vision_items[self.vision_selected_index].add_class("model-item-selected")
            self.selected_vision_model = VISION_MODELS[self.vision_selected_index]
            
            # Scroll to selected
            list_view = self.query_one("#vision-list", ListView)
            list_view.scroll_to_widget(self.vision_items[self.vision_selected_index])
            
            self._update_selection_display()
    
    def _move_selection_up(self):
        """Move selection up in the active tab"""
        if self.active_tab == "planning":
            if self.planning_selected_index > 0:
                self.planning_selected_index -= 1
                self._highlight_planning_selected()
        else:
            if self.vision_selected_index > 0:
                self.vision_selected_index -= 1
                self._highlight_vision_selected()
    
    def _move_selection_down(self):
        """Move selection down in the active tab"""
        if self.active_tab == "planning":
            if self.planning_selected_index < len(PLANNING_MODELS) - 1:
                self.planning_selected_index += 1
                self._highlight_planning_selected()
        else:
            if self.vision_selected_index < len(VISION_MODELS) - 1:
                self.vision_selected_index += 1
                self._highlight_vision_selected()
    
    def _save_models(self):
        """Save the selected models to config"""
        # Update config
        self.config_manager.set_models(
            text_model=self.selected_text_model,
            vision_model=self.selected_vision_model
        )
        
        # Send message and close
        self.post_message(ModelSelected(self.selected_text_model, self.selected_vision_model))
        self.dismiss()
    
    async def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Handle tab switching"""
        if event.tab.id == "planning-tab":
            self.active_tab = "planning"
        elif event.tab.id == "vision-tab":
            self.active_tab = "vision"
    
    async def on_key(self, event: events.Key) -> None:
        """Handle key events"""
        if event.key == "escape":
            self.dismiss()
            event.prevent_default()
        elif event.key == "up":
            self._move_selection_up()
            event.prevent_default()
        elif event.key == "down":
            self._move_selection_down()
            event.prevent_default()
        elif event.key == "tab":
            # Switch tabs
            tabs = self.query_one("#model-tabs", TabbedContent)
            if self.active_tab == "planning":
                tabs.active = "vision-tab"
                self.active_tab = "vision"
            else:
                tabs.active = "planning-tab"
                self.active_tab = "planning"
            event.prevent_default()
        elif event.key == "enter":
            self._save_models()
            event.prevent_default()
    
    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item selection"""
        # Determine which list was clicked
        if event.list_view.id == "planning-list":
            self.planning_selected_index = event.list_view.index
            self._highlight_planning_selected()
        elif event.list_view.id == "vision-list":
            self.vision_selected_index = event.list_view.index
            self._highlight_vision_selected()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "save-btn":
            self._save_models()
        elif event.button.id == "cancel-btn":
            self.dismiss()