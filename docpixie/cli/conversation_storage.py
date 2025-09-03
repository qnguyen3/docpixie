"""
Local conversation storage for DocPixie CLI
Stores conversations per project directory
"""

import json
import uuid
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from docpixie.models.agent import ConversationMessage


@dataclass
class ConversationMetadata:
    """Metadata for a conversation"""
    id: str
    name: str
    working_directory: str
    created_at: str
    updated_at: str
    message_count: int
    indexed_documents: List[str]
    total_cost: float = 0.0


class ConversationStorage:
    """Manages local conversation storage in ./.docpixie/conversations/"""
    
    def __init__(self):
        """Initialize conversation storage for current directory"""
        self.base_path = Path("./.docpixie")
        self.conversations_dir = self.base_path / "conversations"
        self.metadata_file = self.conversations_dir / "metadata.json"
        
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        
        self.working_directory = str(Path.cwd().resolve())
        
        self.current_conversation_id: Optional[str] = None
        
        self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, ConversationMetadata]:
        """Load conversation metadata from file"""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
            
            metadata = {}
            for conv_id, conv_data in data.items():
                if 'total_cost' not in conv_data:
                    conv_data['total_cost'] = 0.0
                metadata[conv_id] = ConversationMetadata(**conv_data)
            
            return metadata
        except Exception as e:
            print(f"Warning: Failed to load conversation metadata: {e}")
            return {}
    
    def _save_metadata(self, metadata: Dict[str, ConversationMetadata]):
        """Save conversation metadata to file"""
        try:
            data = {}
            for conv_id, conv_meta in metadata.items():
                data[conv_id] = asdict(conv_meta)
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving conversation metadata: {e}")
    
    def _conversation_file_path(self, conversation_id: str) -> Path:
        """Get path for conversation file"""
        return self.conversations_dir / f"{conversation_id}.json"
    
    def _generate_conversation_name(self, messages: List[ConversationMessage]) -> str:
        """Generate a conversation name from the first user message"""
        if not messages:
            return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        first_user_message = None
        for msg in messages:
            if msg.role == "user":
                first_user_message = msg
                break
        
        if first_user_message:
            name = first_user_message.content.strip()[:50]
            if len(first_user_message.content) > 50:
                name += "..."
            return name
        else:
            return f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    def create_new_conversation(self, indexed_documents: List[str] = None) -> str:
        """Create a new conversation and return its ID"""
        conversation_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        metadata = ConversationMetadata(
            id=conversation_id,
            name="New Chat",
            working_directory=self.working_directory,
            created_at=now,
            updated_at=now,
            message_count=0,
            indexed_documents=indexed_documents or [],
            total_cost=0.0
        )
        
        conversation_data = {
            "id": conversation_id,
            "metadata": asdict(metadata),
            "messages": []
        }
        
        conversation_file = self._conversation_file_path(conversation_id)
        with open(conversation_file, 'w') as f:
            json.dump(conversation_data, f, indent=2)
        
        all_metadata = self._load_metadata()
        all_metadata[conversation_id] = metadata
        self._save_metadata(all_metadata)
        
        self.current_conversation_id = conversation_id
        return conversation_id
    
    def save_conversation(self, conversation_id: str, messages: List[ConversationMessage], 
                         indexed_documents: List[str] = None):
        """Save conversation messages"""
        try:
            now = datetime.now().isoformat()
            
            messages_data = []
            total_cost = 0.0
            for msg in messages:
                msg_dict = {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                msg_cost = getattr(msg, 'cost', 0.0) or 0.0
                msg_dict["cost"] = msg_cost
                total_cost += msg_cost
                messages_data.append(msg_dict)
            
            all_metadata = self._load_metadata()
            if conversation_id in all_metadata:
                conv_metadata = all_metadata[conversation_id]
                conv_metadata.updated_at = now
                conv_metadata.message_count = len(messages)
                conv_metadata.total_cost = total_cost
                if indexed_documents is not None:
                    conv_metadata.indexed_documents = indexed_documents
                
                if conv_metadata.name == "New Chat" and messages:
                    conv_metadata.name = self._generate_conversation_name(messages)
            else:
                conv_metadata = ConversationMetadata(
                    id=conversation_id,
                    name=self._generate_conversation_name(messages),
                    working_directory=self.working_directory,
                    created_at=now,
                    updated_at=now,
                    message_count=len(messages),
                    indexed_documents=indexed_documents or [],
                    total_cost=total_cost
                )
                all_metadata[conversation_id] = conv_metadata
            
            conversation_data = {
                "id": conversation_id,
                "metadata": asdict(conv_metadata),
                "messages": messages_data
            }
            
            conversation_file = self._conversation_file_path(conversation_id)
            with open(conversation_file, 'w') as f:
                json.dump(conversation_data, f, indent=2)
            
            self._save_metadata(all_metadata)
            
        except Exception as e:
            print(f"Error saving conversation: {e}")
    
    def load_conversation(self, conversation_id: str) -> Optional[tuple[ConversationMetadata, List[ConversationMessage]]]:
        """Load conversation by ID"""
        try:
            conversation_file = self._conversation_file_path(conversation_id)
            if not conversation_file.exists():
                return None
            
            with open(conversation_file, 'r') as f:
                data = json.load(f)
            
            metadata = ConversationMetadata(**data["metadata"])
            
            messages = []
            for msg_data in data["messages"]:
                message = ConversationMessage(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    cost=msg_data.get("cost", 0.0)
                )
                messages.append(message)
            
            self.current_conversation_id = conversation_id
            return metadata, messages
            
        except Exception as e:
            print(f"Error loading conversation: {e}")
            return None
    
    def list_local_conversations(self) -> List[ConversationMetadata]:
        """List conversations from current working directory only"""
        all_metadata = self._load_metadata()
        
        local_conversations = []
        for conv_id, metadata in all_metadata.items():
            if metadata.working_directory == self.working_directory:
                local_conversations.append(metadata)
        
        local_conversations.sort(key=lambda x: x.updated_at, reverse=True)
        return local_conversations
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        try:
            conversation_file = self._conversation_file_path(conversation_id)
            if conversation_file.exists():
                conversation_file.unlink()
            
            all_metadata = self._load_metadata()
            if conversation_id in all_metadata:
                del all_metadata[conversation_id]
                self._save_metadata(all_metadata)
            
            if self.current_conversation_id == conversation_id:
                self.current_conversation_id = None
            
            return True
        except Exception as e:
            print(f"Error deleting conversation: {e}")
            return False
    
    def rename_conversation(self, conversation_id: str, new_name: str) -> bool:
        """Rename a conversation"""
        try:
            all_metadata = self._load_metadata()
            if conversation_id not in all_metadata:
                return False
            
            all_metadata[conversation_id].name = new_name
            all_metadata[conversation_id].updated_at = datetime.now().isoformat()
            
            conversation_file = self._conversation_file_path(conversation_id)
            if conversation_file.exists():
                with open(conversation_file, 'r') as f:
                    data = json.load(f)
                
                data["metadata"]["name"] = new_name
                data["metadata"]["updated_at"] = all_metadata[conversation_id].updated_at
                
                with open(conversation_file, 'w') as f:
                    json.dump(data, f, indent=2)
            
            self._save_metadata(all_metadata)
            return True
            
        except Exception as e:
            print(f"Error renaming conversation: {e}")
            return False
    
    def get_last_conversation(self) -> Optional[str]:
        """Get the most recently updated conversation ID from current directory"""
        conversations = self.list_local_conversations()
        if conversations:
            return conversations[0].id
        return None