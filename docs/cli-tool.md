# DocPixie CLI Tool

DocPixie includes a modern, interactive terminal interface built with Textual that provides a beautiful and intuitive way to chat with your documents.

## 🚀 Quick Start

### Starting the CLI

```bash
# Start the interactive CLI
docpixie
```

## 🎛️ First-Time Setup

When you first run the CLI, you'll be prompted to enter your API key:

```
┌─────────────────────────────────────────────────────────────────┐
│                          Welcome to DocPixie!                   │
│                                                                  │
│          DocPixie needs an OpenRouter API key to work           │
│                    with documents.                               │
│                                                                  │
│              Get your API key from:                              │
│                   https://openrouter.ai/keys                    │
│                                                                  │
│    [                API Key Input                         ]     │
│                                                                  │
│         Press Enter to confirm • Press Esc to quit              │
└─────────────────────────────────────────────────────────────────┘
```

> **Note**: While the setup screen mentions OpenRouter, DocPixie CLI supports all providers (OpenAI, Anthropic, OpenRouter). You can set any provider's API key as an environment variable before starting the CLI.

## 🎨 Interface Overview

The CLI interface consists of several key areas:

```
┌─ DocPixie ──────────────────────────────────── 12:34:56 PM ─┐
│                                                               │
│  ┌─ Chat Area ───────────────────────────────────────────┐  │
│  │                                                        │  │
│  │  Welcome to DocPixie!                                  │  │
│  │  2 documents indexed and ready!                       │  │
│  │                                                        │  │
│  │  Start chatting or type / for commands               │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  Status: Ready • 2 documents indexed                         │
│                                                               │
│  > [                 Input Area                        ]     │
│                                                               │
│  Enter to send • Shift+Enter for new line • Ctrl+/ commands │
│                                                               │
├─────────────────────────────────────────────────────────────┤
│ ^N New  ^L Conversations  ^O Models  ^D Docs  ^/ Cmds  ^Q   │
└─────────────────────────────────────────────────────────────┘
```

## ⌨️ Keyboard Shortcuts

### Global Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Ctrl+N` | New Conversation | Start a fresh conversation |
| `Ctrl+L` | Conversations | Manage conversation history |
| `Ctrl+O` | Model Config | Configure AI models/providers |
| `Ctrl+D` | Documents | Manage documents |
| `Ctrl+/` | Commands | Toggle command palette |
| `Ctrl+Q` | Quit | Exit the application |

### Chat Input Shortcuts

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Enter` | Send Message | Submit your message |
| `Shift+Enter` | New Line | Add line break in message |

## 🛠️ Command System

DocPixie CLI includes a powerful command system. Type `/` to open the command palette or use slash commands directly.

### Available Commands

#### `/new` - New Conversation
Starts a fresh conversation, clearing chat history.

```
> /new
```

#### `/clear` - Clear Chat
Clears the current chat display (conversation is still saved).

```
> /clear
```

#### `/save` - Save Conversation
Manually saves the current conversation to history.

```
> /save
```

#### `/conversations` - Conversation Manager
Opens the conversation management dialog where you can:
- View conversation history
- Load previous conversations
- Delete old conversations

#### `/model` - Model Configuration
Opens the model selector where you can:
- Switch between providers (OpenAI, Anthropic, OpenRouter)
- Configure model settings
- View current model status

#### `/documents` - Document Manager
Opens the document management interface where you can:
- View indexed documents
- Add new documents
- Remove documents from the index
- See document statistics

#### `/exit` - Exit Application
Saves the current conversation and exits the CLI.

```
> /exit
```

### Command Palette

Press `Ctrl+/` or type `/` to open the interactive command palette:

```
┌─ Commands ─────────────────────────────────────────────────┐
│                                                             │
│  > /new                     Start new conversation         │
│    /clear                   Clear current chat             │
│    /save                    Save conversation               │
│    /conversations           Manage conversations           │
│    /model                   Configure AI model             │
│    /documents               Manage documents               │
│    /exit                    Exit DocPixie                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

Use arrow keys to navigate and Enter to select a command.

## 📚 Document Management

### Adding Documents

The CLI automatically discovers and indexes PDF files from a `./documents` directory in your current working directory. Simply:

1. Create a `./documents` folder
2. Copy your PDF files into it
3. Restart the CLI or use the `/documents` command to refresh
───────────────────────────────────────────────────┘
```

### Supported File Types

- **PDF files** (.pdf) - Multi-page documents

### Features

- **Auto-save**: Conversations are automatically saved
- **Context awareness**: Previous messages provide context for new queries
- **Search**: Find conversations by content or title
- **Export**: Save conversations to text files

## 🎯 Chat Features

### Smart Document Analysis

DocPixie's CLI uses an adaptive RAG agent that:

1. **Analyzes your question** to determine if documents are needed
2. **Plans tasks** dynamically based on available documents
3. **Selects relevant pages** using vision AI
4. **Synthesizes responses** from multiple sources
5. **Maintains context** across conversation turns

## ⚙️ Configuration

### CLI Settings

The CLI stores settings in:
- **macOS/Linux**: `~/.docpixie/config.json`
- **Windows**: `%APPDATA%\.docpixie\config.json`

---

The DocPixie CLI provides a powerful, interactive way to work with your documents. Its adaptive AI agent, beautiful interface, and comprehensive features make document analysis both efficient and enjoyable.

Happy chatting! 🚀
