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
    
    def __init__(self, text_model: str, vision_model: str, old_text_model: str = None, old_vision_model: str = None):
        self.text_model = text_model
        self.vision_model = vision_model
        self.old_text_model = old_text_model
        self.old_vision_model = old_vision_model
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
    
    .model-item.--highlight {
        background: $primary;
        color: $text;
    }
    
    .model-item-current {
        background: $success 30%;
        border-left: thick $success;
    }
    
    #button-container {
        align: center middle;
        margin-top: 1;
        height: 3;
    }
    
    Button {
        min-width: 16;
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
        
        # Track which tab is active and cursor positions
        self.active_tab = "planning"
        self.planning_index = 0
        self.vision_index = 0
    
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
                    list_view = ListView(id="planning-list")
                    list_view.can_focus = False  # Disable focus
                    yield list_view
                
                with TabPane("Vision Model", id="vision-tab"):
                    yield Static(
                        "Select model for vision and images:",
                        classes="tab-info"
                    )
                    list_view = ListView(id="vision-list")
                    list_view.can_focus = False  # Disable focus
                    yield list_view
            
            # Current selection display
            yield Static(id="current-selection", classes="info")
            
            # Action buttons
            with Horizontal(id="button-container"):
                yield Button("Cancel", variant="default", id="cancel-btn")
    
    async def on_mount(self):
        """Load models when dialog mounts"""
        await self._load_planning_models()
        await self._load_vision_models()
        self._update_status_display()
        
        # Set initial focus to the dialog itself
        self.focus()
    
    async def _load_planning_models(self):
        """Load and display planning models"""
        list_view = self.query_one("#planning-list", ListView)
        list_view.clear()
        
        for i, model in enumerate(PLANNING_MODELS):
            # Create model item with indicator for current model
            if model == self.current_text_model:
                model_display = f"[green bold]✓[/green bold] [bold]{model}[/bold] [dim](current)[/dim]"
                # Set initial cursor to current model
                self.planning_index = i
            else:
                model_display = f"  {model}"
            
            list_item = ListItem(Label(model_display), classes="model-item")
            
            # Mark current model with style
            if model == self.current_text_model:
                list_item.add_class("model-item-current")
            
            list_view.append(list_item)
        
        # Set the cursor to the current model
        list_view.index = self.planning_index
    
    async def _load_vision_models(self):
        """Load and display vision models"""
        list_view = self.query_one("#vision-list", ListView)
        list_view.clear()
        
        for i, model in enumerate(VISION_MODELS):
            # Create model item with indicator for current model
            if model == self.current_vision_model:
                model_display = f"[green bold]✓[/green bold] [bold]{model}[/bold] [dim](current)[/dim]"
                # Set initial cursor to current model
                self.vision_index = i
            else:
                model_display = f"  {model}"
            
            list_item = ListItem(Label(model_display), classes="model-item")
            
            # Mark current model with style
            if model == self.current_vision_model:
                list_item.add_class("model-item-current")
            
            list_view.append(list_item)
        
        # Set the cursor to the current model
        list_view.index = self.vision_index
    
    def _update_status_display(self):
        """Update the current selection display"""
        selection_display = self.query_one("#current-selection", Static)
        
        # Get the currently highlighted models based on active tab
        if self.active_tab == "planning":
            highlighted_text = PLANNING_MODELS[self.planning_index] if self.planning_index < len(PLANNING_MODELS) else self.current_text_model
            highlighted_vision = self.current_vision_model
        else:
            highlighted_text = self.current_text_model
            highlighted_vision = VISION_MODELS[self.vision_index] if self.vision_index < len(VISION_MODELS) else self.current_vision_model
        
        # Format display with clear indication of what's selected
        text_display = f"[cyan]{highlighted_text}[/cyan]" if highlighted_text == self.current_text_model else f"[yellow]→ {highlighted_text}[/yellow]"
        vision_display = f"[magenta]{highlighted_vision}[/magenta]" if highlighted_vision == self.current_vision_model else f"[yellow]→ {highlighted_vision}[/yellow]"
        
        # Show which tab is active
        if self.active_tab == "planning":
            display_text = f"[dim]Planning:[/dim] {text_display} [bold]◄[/bold] [dim]|[/dim] [dim]Vision:[/dim] {vision_display}"
        else:
            display_text = f"[dim]Planning:[/dim] {text_display} [dim]|[/dim] [dim]Vision:[/dim] {vision_display} [bold]◄[/bold]"
        
        selection_display.update(display_text)
    
    async def _switch_and_save_model(self):
        """Switch to the selected model immediately"""
        if self.active_tab == "planning":
            if self.planning_index < len(PLANNING_MODELS):
                new_model = PLANNING_MODELS[self.planning_index]
                if new_model != self.current_text_model:
                    # Send message with old and new models BEFORE updating config
                    self.post_message(ModelSelected(
                        new_model, 
                        self.current_vision_model,
                        self.current_text_model,
                        self.current_vision_model
                    ))
                    # Now update config
                    self.config_manager.set_models(
                        text_model=new_model,
                        vision_model=self.current_vision_model
                    )
        else:
            if self.vision_index < len(VISION_MODELS):
                new_model = VISION_MODELS[self.vision_index]
                if new_model != self.current_vision_model:
                    # Send message with old and new models BEFORE updating config
                    self.post_message(ModelSelected(
                        self.current_text_model, 
                        new_model,
                        self.current_text_model,
                        self.current_vision_model
                    ))
                    # Now update config
                    self.config_manager.set_models(
                        text_model=self.current_text_model,
                        vision_model=new_model
                    )
        
        # Close dialog
        self.dismiss()
    
    async def _switch_to_planning_tab(self):
        """Switch to planning tab"""
        self.active_tab = "planning"
        tabs = self.query_one("#model-tabs", TabbedContent)
        tabs.active = "planning-tab"
        
        # Update planning list view cursor
        planning_list = self.query_one("#planning-list", ListView)
        planning_list.index = self.planning_index
        
        self._update_status_display()
    
    async def _switch_to_vision_tab(self):
        """Switch to vision tab"""
        self.active_tab = "vision"
        tabs = self.query_one("#model-tabs", TabbedContent)
        tabs.active = "vision-tab"
        
        # Update vision list view cursor
        vision_list = self.query_one("#vision-list", ListView)
        vision_list.index = self.vision_index
        
        self._update_status_display()
    
    async def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Handle tab switching from TabbedContent (e.g., mouse clicks on tabs)"""
        if event.tab.id == "planning-tab":
            self.active_tab = "planning"
            # Ensure planning list has correct index
            list_view = self.query_one("#planning-list", ListView)
            list_view.index = self.planning_index
        elif event.tab.id == "vision-tab":
            self.active_tab = "vision"
            # Ensure vision list has correct index
            list_view = self.query_one("#vision-list", ListView)
            list_view.index = self.vision_index
        
        self._update_status_display()
    
    async def on_key(self, event: events.Key) -> None:
        """Handle all key events for the dialog"""
        # Always prevent default to stop ListView from handling keys
        event.prevent_default()
        event.stop()
        
        if event.key == "escape":
            self.dismiss()
            
        elif event.key == "enter":
            # Select current item and close
            await self._switch_and_save_model()
            
        elif event.key == "up":
            # Move selection up in the active tab
            if self.active_tab == "planning":
                if self.planning_index > 0:
                    self.planning_index -= 1
                    list_view = self.query_one("#planning-list", ListView)
                    list_view.index = self.planning_index
                    self._update_status_display()
            else:
                if self.vision_index > 0:
                    self.vision_index -= 1
                    list_view = self.query_one("#vision-list", ListView)
                    list_view.index = self.vision_index
                    self._update_status_display()
            
        elif event.key == "down":
            # Move selection down in the active tab
            if self.active_tab == "planning":
                if self.planning_index < len(PLANNING_MODELS) - 1:
                    self.planning_index += 1
                    list_view = self.query_one("#planning-list", ListView)
                    list_view.index = self.planning_index
                    self._update_status_display()
            else:
                if self.vision_index < len(VISION_MODELS) - 1:
                    self.vision_index += 1
                    list_view = self.query_one("#vision-list", ListView)
                    list_view.index = self.vision_index
                    self._update_status_display()
            
        elif event.key in ["tab", "right"]:
            # Switch to next tab
            if self.active_tab == "planning":
                await self._switch_to_vision_tab()
            else:
                await self._switch_to_planning_tab()
            
        elif event.key == "left":
            # Switch to previous tab
            if self.active_tab == "vision":
                await self._switch_to_planning_tab()
            else:
                await self._switch_to_vision_tab()
    
    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle list item selection (double click or mouse selection)"""
        # Update the appropriate index based on which list was clicked
        if event.list_view.id == "planning-list":
            self.planning_index = event.list_view.index
            self.active_tab = "planning"
            # Make sure the tab is switched
            await self._switch_to_planning_tab()
        elif event.list_view.id == "vision-list":
            self.vision_index = event.list_view.index
            self.active_tab = "vision"
            # Make sure the tab is switched
            await self._switch_to_vision_tab()
        
        # Select and close
        await self._switch_and_save_model()
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        if event.button.id == "cancel-btn":
            self.dismiss()