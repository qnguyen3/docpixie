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
        width: 70;
        height: auto;
        max-height: 30;
        min-height: 24;
        padding: 1;
        background: $surface;
        border: solid $primary;
        overflow-y: auto;
    }

    .title {
        height: 1;
        margin: 0 0 1 0;
    }

    #model-tabs {
        height: 16;
        margin: 0;
    }

    #planning-list, #vision-list {
        height: 10;
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
        height: 2;
        margin: 1 0;
    }

    #controls-hint {
        height: 2;
        align: center middle;
        color: $text-muted;
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
        self.active_tab = "planning"
        self.planning_index = 0
        self.vision_index = 0

    def compose(self):
        with Container(id="dialog-container"):
            yield Static("[bold]🤖 Model Configuration[/bold]", classes="title")

            with TabbedContent(id="model-tabs"):
                with TabPane("Planning Model", id="planning-tab"):
                    yield Static(
                        "Select model for planning and text:",
                        classes="tab-info"
                    )
                    list_view = ListView(id="planning-list")
                    list_view.can_focus = False
                    yield list_view

                with TabPane("Vision Model", id="vision-tab"):
                    yield Static(
                        "Select model for vision and images:",
                        classes="tab-info"
                    )
                    list_view = ListView(id="vision-list")
                    list_view.can_focus = False
                    yield list_view

            yield Static(id="current-selection", classes="info")
            yield Static(
                "[dim]↑↓[/dim] Navigate  [dim]←→[/dim] Switch Tab  [dim]Enter[/dim] Select  [dim]Esc[/dim] Cancel",
                id="controls-hint"
            )

    async def on_mount(self):
        await self._load_models("planning")
        await self._load_models("vision")
        self._update_status_display()
        self.focus()

    async def _load_models(self, model_type: str):
        if model_type == "planning":
            models = PLANNING_MODELS
            current_model = self.current_text_model
            list_id = "#planning-list"
        else:
            models = VISION_MODELS
            current_model = self.current_vision_model
            list_id = "#vision-list"

        list_view = self.query_one(list_id, ListView)
        list_view.clear()

        for i, model in enumerate(models):
            is_current = model == current_model
            list_item = self._create_model_item(model, is_current)
            list_view.append(list_item)
            
            if is_current:
                if model_type == "planning":
                    self.planning_index = i
                else:
                    self.vision_index = i

        list_view.index = self.planning_index if model_type == "planning" else self.vision_index

    def _create_model_item(self, model: str, is_current: bool) -> ListItem:
        if is_current:
            model_display = f"[green bold]✓[/green bold] [bold]{model}[/bold] [dim](current)[/dim]"
        else:
            model_display = f"  {model}"

        list_item = ListItem(Label(model_display), classes="model-item")
        if is_current:
            list_item.add_class("model-item-current")
        return list_item

    def _update_status_display(self):
        selection_display = self.query_one("#current-selection", Static)

        if self.active_tab == "planning":
            highlighted_text = PLANNING_MODELS[self.planning_index] if self.planning_index < len(PLANNING_MODELS) else self.current_text_model
            highlighted_vision = self.current_vision_model
        else:
            highlighted_text = self.current_text_model
            highlighted_vision = VISION_MODELS[self.vision_index] if self.vision_index < len(VISION_MODELS) else self.current_vision_model

        text_display = f"[cyan]{highlighted_text}[/cyan]" if highlighted_text == self.current_text_model else f"[yellow]→ {highlighted_text}[/yellow]"
        vision_display = f"[magenta]{highlighted_vision}[/magenta]" if highlighted_vision == self.current_vision_model else f"[yellow]→ {highlighted_vision}[/yellow]"

        active_marker = "[bold]◄[/bold]"
        if self.active_tab == "planning":
            display_text = f"[dim]Planning:[/dim] {text_display} {active_marker}\n[dim]Vision:[/dim]   {vision_display}"
        else:
            display_text = f"[dim]Planning:[/dim] {text_display}\n[dim]Vision:[/dim]   {vision_display} {active_marker}"

        selection_display.update(display_text)

    async def _switch_and_save_model(self):
        if self.active_tab == "planning":
            models = PLANNING_MODELS
            index = self.planning_index
            current_model = self.current_text_model
        else:
            models = VISION_MODELS
            index = self.vision_index
            current_model = self.current_vision_model

        if index < len(models):
            new_model = models[index]
            if new_model != current_model:
                if self.active_tab == "planning":
                    self.post_message(ModelSelected(
                        new_model,
                        self.current_vision_model,
                        self.current_text_model,
                        self.current_vision_model
                    ))
                    self.config_manager.set_models(
                        text_model=new_model,
                        vision_model=self.current_vision_model
                    )
                else:
                    self.post_message(ModelSelected(
                        self.current_text_model,
                        new_model,
                        self.current_text_model,
                        self.current_vision_model
                    ))
                    self.config_manager.set_models(
                        text_model=self.current_text_model,
                        vision_model=new_model
                    )

        self.dismiss()

    async def _switch_tab(self, tab_name: str):
        self.active_tab = tab_name
        tabs = self.query_one("#model-tabs", TabbedContent)
        tabs.active = f"{tab_name}-tab"
        
        list_id = f"#{tab_name}-list"
        list_view = self.query_one(list_id, ListView)
        list_view.index = self.planning_index if tab_name == "planning" else self.vision_index
        
        self._update_status_display()

    async def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.tab.id == "planning-tab":
            self.active_tab = "planning"
            list_view = self.query_one("#planning-list", ListView)
            list_view.index = self.planning_index
        elif event.tab.id == "vision-tab":
            self.active_tab = "vision"
            list_view = self.query_one("#vision-list", ListView)
            list_view.index = self.vision_index
        self._update_status_display()

    async def on_key(self, event: events.Key) -> None:
        event.prevent_default()
        event.stop()

        if event.key == "escape":
            self.dismiss()
        elif event.key == "enter":
            await self._switch_and_save_model()
        elif event.key == "up":
            self._move_selection(-1)
        elif event.key == "down":
            self._move_selection(1)
        elif event.key in ["tab", "right"]:
            await self._switch_tab("vision" if self.active_tab == "planning" else "planning")
        elif event.key == "left":
            await self._switch_tab("planning" if self.active_tab == "vision" else "vision")
    
    def _move_selection(self, direction: int):
        if self.active_tab == "planning":
            models = PLANNING_MODELS
            current_index = self.planning_index
        else:
            models = VISION_MODELS
            current_index = self.vision_index
        
        new_index = current_index + direction
        if 0 <= new_index < len(models):
            if self.active_tab == "planning":
                self.planning_index = new_index
                list_id = "#planning-list"
            else:
                self.vision_index = new_index
                list_id = "#vision-list"
            
            list_view = self.query_one(list_id, ListView)
            list_view.index = new_index
            self._update_status_display()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "planning-list":
            self.planning_index = event.list_view.index
            self.active_tab = "planning"
            await self._switch_tab("planning")
        elif event.list_view.id == "vision-list":
            self.vision_index = event.list_view.index
            self.active_tab = "vision"
            await self._switch_tab("vision")
        await self._switch_and_save_model()
