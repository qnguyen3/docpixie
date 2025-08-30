# Storage Options in DocPixie

DocPixie provides a flexible storage layer for managing documents and their processed images. The storage system is pluggable, allowing you to use local filesystem, in-memory storage, or cloud storage like AWS S3.

## Storage Architecture

```
BaseStorage (Abstract)
    ├── LocalStorage     # Filesystem storage
    ├── InMemoryStorage  # RAM storage (testing)
    └── S3Storage        # Cloud storage (example below)
```

## Built-in Storage Backends

### Local Storage (Default)

Stores documents and images on the local filesystem:

```python
from docpixie import create_docpixie

# Uses ./docpixie_data by default
pixie = create_docpixie(provider="openai")

# Custom storage path
pixie = create_docpixie(
    provider="openai",
    storage_path="/path/to/documents"
)
```

**Directory Structure:**
```
docpixie_data/
├── documents/
│   ├── doc_abc123/
│   │   ├── metadata.json
│   │   └── pages/
│   │       ├── page_001.jpg
│   │       ├── page_002.jpg
│   │       └── ...
│   └── doc_xyz789/
│       └── ...
└── index.json
```

### In-Memory Storage

Keeps everything in RAM - perfect for testing and temporary workflows:

```python
from docpixie import create_memory_docpixie

# No files written to disk
pixie = create_memory_docpixie(provider="openai")

# Process documents
doc = pixie.add_document_sync("report.pdf")

# Everything is lost when program exits
```

## Implementing S3 Storage

Here's a complete implementation of S3 storage for DocPixie:

### Installation

```bash
# Install AWS SDK
pip install boto3

# For MinIO or S3-compatible storage
pip install boto3 minio
```

### S3 Storage Implementation

```python
# s3_storage.py
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
import tempfile
import io

import boto3
from botocore.exceptions import ClientError

from docpixie.storage.base import BaseStorage
from docpixie.models.document import Document, Page, DocumentStatus
from docpixie.core.config import DocPixieConfig

logger = logging.getLogger(__name__)


class S3Storage(BaseStorage):
    """
    AWS S3 storage backend for DocPixie
    Also compatible with MinIO and other S3-compatible services
    """
    
    def __init__(
        self, 
        config: DocPixieConfig,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: str = 'us-east-1',
        endpoint_url: Optional[str] = None  # For MinIO/custom S3
    ):
        """
        Initialize S3 storage
        
        Args:
            config: DocPixie configuration
            bucket_name: S3 bucket name
            aws_access_key_id: AWS access key (uses env/IAM if None)
            aws_secret_access_key: AWS secret key
            aws_region: AWS region
            endpoint_url: Custom endpoint (for MinIO/S3-compatible)
        """
        self.config = config
        self.bucket_name = bucket_name
        
        # Initialize S3 client
        session_config = {}
        if aws_access_key_id:
            session_config['aws_access_key_id'] = aws_access_key_id
        if aws_secret_access_key:
            session_config['aws_secret_access_key'] = aws_secret_access_key
        
        self.s3_client = boto3.client(
            's3',
            region_name=aws_region,
            endpoint_url=endpoint_url,
            **session_config
        )
        
        # Verify bucket exists or create it
        self._ensure_bucket_exists()
        
        # Cache for document metadata
        self._metadata_cache = {}
        
        logger.info(f"Initialized S3 storage with bucket: {bucket_name}")
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Create bucket
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created S3 bucket: {self.bucket_name}")
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
                    raise
            else:
                raise
    
    async def save_document(self, document: Document) -> str:
        """Save document to S3"""
        try:
            # Prepare document metadata
            metadata = {
                'id': document.id,
                'name': document.name,
                'summary': document.summary or '',
                'status': document.status.value,
                'page_count': document.page_count,
                'created_at': document.created_at.isoformat(),
                'metadata': document.metadata
            }
            
            # Save metadata to S3
            metadata_key = f"documents/{document.id}/metadata.json"
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json'
            )
            
            # Save each page image
            for page in document.pages:
                # Read local image file
                with open(page.image_path, 'rb') as f:
                    image_data = f.read()
                
                # Upload to S3
                page_key = f"documents/{document.id}/pages/page_{page.page_number:03d}.jpg"
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=page_key,
                    Body=image_data,
                    ContentType='image/jpeg'
                )
                
                # Update page object with S3 path
                page.metadata['s3_key'] = page_key
                page.metadata['s3_bucket'] = self.bucket_name
            
            # Update index
            await self._update_index(document.id, metadata)
            
            logger.info(f"Saved document {document.id} to S3")
            return document.id
            
        except Exception as e:
            logger.error(f"Failed to save document to S3: {e}")
            raise StorageError(f"S3 save failed: {e}", document.id)
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve document from S3"""
        try:
            # Get metadata
            metadata_key = f"documents/{document_id}/metadata.json"
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=metadata_key
            )
            metadata = json.loads(response['Body'].read())
            
            # List and download page images
            pages = []
            prefix = f"documents/{document_id}/pages/"
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            # Create temp directory for images
            temp_dir = tempfile.mkdtemp(prefix="docpixie_s3_")
            
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            for page_response in page_iterator:
                if 'Contents' not in page_response:
                    continue
                    
                for obj in page_response['Contents']:
                    # Download page image
                    page_num = int(obj['Key'].split('_')[-1].split('.')[0])
                    
                    local_path = f"{temp_dir}/page_{page_num:03d}.jpg"
                    self.s3_client.download_file(
                        self.bucket_name,
                        obj['Key'],
                        local_path
                    )
                    
                    # Create Page object
                    page = Page(
                        page_number=page_num,
                        image_path=local_path,
                        metadata={
                            's3_key': obj['Key'],
                            's3_bucket': self.bucket_name
                        }
                    )
                    pages.append(page)
            
            # Sort pages by number
            pages.sort(key=lambda p: p.page_number)
            
            # Create Document object
            document = Document(
                id=metadata['id'],
                name=metadata['name'],
                pages=pages,
                summary=metadata.get('summary'),
                status=DocumentStatus(metadata['status']),
                metadata=metadata.get('metadata', {})
            )
            
            return document
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            logger.error(f"Failed to get document from S3: {e}")
            raise StorageError(f"S3 retrieval failed: {e}", document_id)
    
    async def list_documents(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """List all documents in S3"""
        try:
            # Get index from S3
            try:
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key="index.json"
                )
                index = json.loads(response['Body'].read())
            except ClientError:
                # No index yet
                index = {}
            
            # Convert to list
            documents = list(index.values())
            
            # Apply limit
            if limit:
                documents = documents[:limit]
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete document from S3"""
        try:
            # List all objects with document prefix
            prefix = f"documents/{document_id}/"
            paginator = self.s3_client.get_paginator('list_objects_v2')
            
            # Collect all keys to delete
            keys_to_delete = []
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            for page_response in page_iterator:
                if 'Contents' in page_response:
                    for obj in page_response['Contents']:
                        keys_to_delete.append({'Key': obj['Key']})
            
            # Delete all objects
            if keys_to_delete:
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': keys_to_delete}
                )
            
            # Update index
            await self._remove_from_index(document_id)
            
            logger.info(f"Deleted document {document_id} from S3")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False
    
    async def document_exists(self, document_id: str) -> bool:
        """Check if document exists in S3"""
        try:
            metadata_key = f"documents/{document_id}/metadata.json"
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=metadata_key
            )
            return True
        except ClientError:
            return False
    
    async def get_document_summary(self, document_id: str) -> Optional[str]:
        """Get document summary without downloading all pages"""
        try:
            metadata_key = f"documents/{document_id}/metadata.json"
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=metadata_key
            )
            metadata = json.loads(response['Body'].read())
            return metadata.get('summary')
        except ClientError:
            return None
    
    async def update_document_summary(self, document_id: str, summary: str) -> bool:
        """Update document summary in S3"""
        try:
            # Get existing metadata
            metadata_key = f"documents/{document_id}/metadata.json"
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=metadata_key
            )
            metadata = json.loads(response['Body'].read())
            
            # Update summary
            metadata['summary'] = summary
            
            # Save back to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json'
            )
            
            # Update index
            await self._update_index(document_id, metadata)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update summary: {e}")
            return False
    
    async def get_all_documents(self) -> List[Document]:
        """Get all documents for agent processing"""
        documents = []
        doc_list = await self.list_documents()
        
        for doc_meta in doc_list:
            doc = await self.get_document(doc_meta['id'])
            if doc:
                documents.append(doc)
        
        return documents
    
    async def get_all_pages(self) -> List[Page]:
        """Get all pages from all documents"""
        all_pages = []
        documents = await self.get_all_documents()
        
        for doc in documents:
            all_pages.extend(doc.pages)
        
        return all_pages
    
    async def _update_index(self, document_id: str, metadata: dict):
        """Update document index in S3"""
        try:
            # Get current index
            try:
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key="index.json"
                )
                index = json.loads(response['Body'].read())
            except ClientError:
                index = {}
            
            # Update index
            index[document_id] = {
                'id': document_id,
                'name': metadata['name'],
                'summary': metadata.get('summary', '')[:200],
                'page_count': metadata['page_count'],
                'created_at': metadata['created_at']
            }
            
            # Save index
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key="index.json",
                Body=json.dumps(index, indent=2),
                ContentType='application/json'
            )
            
        except Exception as e:
            logger.error(f"Failed to update index: {e}")
    
    async def _remove_from_index(self, document_id: str):
        """Remove document from index"""
        try:
            # Get current index
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key="index.json"
            )
            index = json.loads(response['Body'].read())
            
            # Remove document
            index.pop(document_id, None)
            
            # Save index
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key="index.json",
                Body=json.dumps(index, indent=2),
                ContentType='application/json'
            )
            
        except Exception as e:
            logger.error(f"Failed to update index: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get S3 storage statistics"""
        try:
            # Get bucket size
            total_size = 0
            total_objects = 0
            
            paginator = self.s3_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(Bucket=self.bucket_name)
            
            for page in page_iterator:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        total_objects += 1
            
            return {
                'backend': 'S3Storage',
                'bucket': self.bucket_name,
                'total_objects': total_objects,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'features': ['cloud_storage', 'scalable', 'distributed']
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {'backend': 'S3Storage', 'error': str(e)}


# Exception class if not imported
class StorageError(Exception):
    """Storage operation error"""
    def __init__(self, message: str, document_id: Optional[str] = None):
        self.document_id = document_id
        super().__init__(message)
```

### Using S3 Storage

```python
from docpixie import DocPixie
from docpixie.core.config import DocPixieConfig
from s3_storage import S3Storage

# Configure DocPixie
config = DocPixieConfig(provider="openai")

# Create S3 storage
s3_storage = S3Storage(
    config=config,
    bucket_name="docpixie-documents",
    aws_access_key_id="YOUR_ACCESS_KEY",
    aws_secret_access_key="YOUR_SECRET_KEY",
    aws_region="us-west-2"
)

# Initialize DocPixie with S3 storage
pixie = DocPixie(config=config, storage=s3_storage)

# Use normally
doc = pixie.add_document_sync("report.pdf")
result = pixie.query_sync("What are the key findings?")
```

### Using with MinIO (S3-Compatible)

```python
# MinIO configuration
s3_storage = S3Storage(
    config=config,
    bucket_name="docpixie",
    aws_access_key_id="minioadmin",
    aws_secret_access_key="minioadmin",
    endpoint_url="http://localhost:9000"  # MinIO endpoint
)

pixie = DocPixie(config=config, storage=s3_storage)
```

### Environment Configuration

```bash
# AWS S3
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-west-2"

# MinIO
export MINIO_ENDPOINT="http://localhost:9000"
export MINIO_ACCESS_KEY="minioadmin"
export MINIO_SECRET_KEY="minioadmin"
```

## Creating Custom Storage Backends

Implement the BaseStorage interface for any storage system:

```python
from docpixie.storage.base import BaseStorage
from typing import List, Optional, Dict, Any
import redis
import json

class RedisStorage(BaseStorage):
    """Example Redis storage backend"""
    
    def __init__(self, config, redis_url="redis://localhost:6379"):
        self.config = config
        self.redis_client = redis.from_url(redis_url)
    
    async def save_document(self, document: Document) -> str:
        # Serialize document
        doc_data = {
            'id': document.id,
            'name': document.name,
            'summary': document.summary,
            'pages': [
                {
                    'page_number': p.page_number,
                    'image_path': p.image_path,
                    'metadata': p.metadata
                }
                for p in document.pages
            ]
        }
        
        # Save to Redis
        key = f"doc:{document.id}"
        self.redis_client.set(key, json.dumps(doc_data))
        
        # Add to index
        self.redis_client.sadd("doc:index", document.id)
        
        return document.id
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        key = f"doc:{document_id}"
        data = self.redis_client.get(key)
        
        if not data:
            return None
        
        doc_data = json.loads(data)
        
        # Reconstruct document
        pages = [
            Page(
                page_number=p['page_number'],
                image_path=p['image_path'],
                metadata=p['metadata']
            )
            for p in doc_data['pages']
        ]
        
        return Document(
            id=doc_data['id'],
            name=doc_data['name'],
            pages=pages,
            summary=doc_data.get('summary')
        )
    
    # Implement other required methods...
```

## Storage Comparison

| Storage Type | Use Case | Pros | Cons |
|-------------|----------|------|------|
| **Local** | Development, Single server | Fast, Simple | Not scalable |
| **Memory** | Testing, Temporary | Very fast | Data lost on restart |
| **S3** | Production, Multi-server | Scalable, Durable | Network latency |
| **Redis** | Caching, Fast access | Fast retrieval | Memory limits |
| **MongoDB** | Flexible queries | Rich queries | More complex |

## Performance Optimization

### Caching Layer

Add caching to any storage backend:

```python
from functools import lru_cache
import hashlib

class CachedStorage(BaseStorage):
    """Wrapper that adds caching to any storage backend"""
    
    def __init__(self, base_storage: BaseStorage):
        self.storage = base_storage
        self._cache = {}
    
    @lru_cache(maxsize=100)
    async def get_document(self, document_id: str) -> Optional[Document]:
        # Check cache first
        if document_id in self._cache:
            return self._cache[document_id]
        
        # Fetch from storage
        doc = await self.storage.get_document(document_id)
        if doc:
            self._cache[document_id] = doc
        
        return doc
    
    async def save_document(self, document: Document) -> str:
        # Save to storage
        doc_id = await self.storage.save_document(document)
        
        # Update cache
        self._cache[doc_id] = document
        
        return doc_id
```

### Compression

Reduce storage size with compression:

```python
import gzip
import base64

def compress_image(image_path: str) -> bytes:
    """Compress image for storage"""
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    compressed = gzip.compress(image_data, compresslevel=6)
    return base64.b64encode(compressed)

def decompress_image(compressed_data: bytes) -> bytes:
    """Decompress image from storage"""
    decoded = base64.b64decode(compressed_data)
    return gzip.decompress(decoded)
```

## Best Practices

### 1. Connection Pooling
```python
# Use connection pools for database storage
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@localhost/db",
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

### 2. Async Operations
```python
# Use async for better concurrency
import asyncio

async def process_multiple_documents(pixie, file_paths):
    tasks = [
        pixie.add_document(path) 
        for path in file_paths
    ]
    return await asyncio.gather(*tasks)
```

### 3. Error Handling
```python
from docpixie.storage.base import StorageError

try:
    document = await storage.get_document(doc_id)
except StorageError as e:
    logger.error(f"Storage error: {e}")
    # Fallback or retry logic
```

### 4. Cleanup
```python
# Clean up temporary files
import tempfile
import shutil

class TempFileManager:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
    
    def __enter__(self):
        return self.temp_dir
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
```

## Next Steps

- Review [Data Models](models.md) to understand storage structures
- See [Document Processing](document-processing.md) for input handling
- Check [Getting Started](getting-started.md) for usage examples