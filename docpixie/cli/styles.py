"""
CSS styles for DocPixie CLI components
"""

SETUP_SCREEN_CSS = """
SetupScreen {
    align: center middle;
}

#setup-container {
    width: 80;
    height: auto;
    padding: 2;
    border: solid $primary;
}

#api-input {
    margin: 1 0;
}

#button-container {
    align: center middle;
    margin-top: 1;
}
"""

MAIN_APP_CSS = """
#chat-container {
    height: 100%;
    layout: vertical;
    background: #2d1f2d;
    padding: 0 1 1 1;
}

#chat-log {
    border: solid #4a3344;
    background: #2d1f2d;
}

#input-container {
    height: auto;
    min-height: 3;
    max-height: 12;
    padding: 0 0 0 1;
    margin: 0;
    background: #2d1f2d;
    border: solid #ff99cc;
}

#prompt-indicator {
    width: 2;
    color: #ff99cc;
    padding: 0;
    background: #2d1f2d;
    margin: 0;
}

#chat-input {
    background: #2d1f2d;
    min-height: 1;
    max-height: 10;
    height: auto;
    border: none;
    padding: 0;
    margin: 0;
    scrollbar-background: #2d1f2d;
    scrollbar-color: #ff99cc;
    scrollbar-size: 1 1;
}

#chat-input:focus {
    border: none;
}

#chat-input > .text-area--scrollbar {
    background: #2d1f2d;
}

#chat-input > ScrollableContainer {
    background: #2d1f2d;
}

ChatInput {
    background: #2d1f2d !important;
}

ChatInput > .text-area--scrollbar {
    background: #2d1f2d;
}

ChatInput .text-area--cursor-line {
    background: #2d1f2d;
}

#chat-input .text-area--document {
    background: #2d1f2d;
}

#chat-input .text-area--selection {
    background: #4a3344;
}

#chat-input .text-area--cursor {
    background: #ff99cc;
}

#input-hint {
    height: 1;
    color: #bda6b6;
    background: #2d1f2d;
    padding: 0 1;
    margin: 0;
}

#status-bar {
    height: 1;
    background: #2d1f2d;
    color: $text;
    padding: 0 1;
}

.user-message {
    color: $success;
    margin: 0 0 1 0;
}

.assistant-message {
    color: $primary;
    margin: 0 0 1 0;
}

.task-update {
    color: $warning;
    margin: 0 0 1 0;
}

.error-message {
    color: $error;
    margin: 0 0 1 0;
}
"""