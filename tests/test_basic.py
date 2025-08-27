"""
Basic tests for DocPixie Phase 1 functionality
"""

import pytest
import tempfile
import os
from pathlib import Path

from docpixie.core.config import DocPixieConfig
from docpixie.models.document import Document, Page, QueryMode, DocumentStatus
from docpixie.storage.memory import InMemoryStorage
from docpixie.processors.factory import ProcessorFactory
from docpixie.docpixie import DocPixie, create_memory_docpixie


class TestDocPixieConfig:
    """Test configuration system"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = DocPixieConfig()
        
        assert config.provider == "openai"
        assert config.storage_type == "local"
        assert config.flash_max_pages == 5
        assert config.pro_max_pages == 15
        assert config.pdf_render_scale == 2.0
        assert config.jpeg_quality == 90
    
    def test_config_validation(self):
        """Test configuration validation"""
        # Test invalid JPEG quality
        with pytest.raises(ValueError):
            DocPixieConfig(jpeg_quality=150)
        
        # Test invalid PDF scale
        with pytest.raises(ValueError):
            DocPixieConfig(pdf_render_scale=0)
    
    def test_mode_config(self):
        """Test mode-specific configuration"""
        config = DocPixieConfig()
        
        flash_config = config.get_mode_config("flash")
        assert flash_config['max_pages'] == 5
        assert flash_config['vision_detail'] == "low"
        
        pro_config = config.get_mode_config("pro")
        assert pro_config['max_pages'] == 15
        assert pro_config['vision_detail'] == "high"


class TestDocumentModels:
    """Test document models"""
    
    def test_page_creation(self):
        """Test Page model creation"""
        page = Page(
            page_number=1,
            image_path="/test/path.jpg",
            content_summary="Test summary"
        )
        
        assert page.page_number == 1
        assert page.image_path == "/test/path.jpg"
        assert page.content_summary == "Test summary"
    
    def test_page_validation(self):
        """Test Page model validation"""
        # Test invalid page number
        with pytest.raises(ValueError):
            Page(page_number=0, image_path="/test/path.jpg")
        
        # Test missing image path
        with pytest.raises(ValueError):
            Page(page_number=1, image_path="")
    
    def test_document_creation(self):
        """Test Document model creation"""
        pages = [
            Page(page_number=1, image_path="/test/page1.jpg"),
            Page(page_number=2, image_path="/test/page2.jpg")
        ]
        
        doc = Document(
            id="test-doc",
            name="Test Document",
            pages=pages
        )
        
        assert doc.id == "test-doc"
        assert doc.name == "Test Document"
        assert doc.page_count == 2
        assert len(doc.pages) == 2
    
    def test_document_methods(self):
        """Test Document model methods"""
        pages = [
            Page(page_number=1, image_path="/test/page1.jpg"),
            Page(page_number=2, image_path="/test/page2.jpg"),
            Page(page_number=3, image_path="/test/page3.jpg")
        ]
        
        doc = Document(id="test", name="Test", pages=pages)
        
        # Test get_page
        page = doc.get_page(2)
        assert page is not None
        assert page.page_number == 2
        
        # Test get_pages_range
        range_pages = doc.get_pages_range(1, 2)
        assert len(range_pages) == 2
        assert range_pages[0].page_number == 1
        assert range_pages[1].page_number == 2


class TestInMemoryStorage:
    """Test in-memory storage backend"""
    
    def test_storage_creation(self):
        """Test storage creation"""
        config = DocPixieConfig(storage_type="memory")
        storage = InMemoryStorage(config)
        
        assert storage.get_document_count() == 0
        assert storage.get_total_pages() == 0
    
    @pytest.mark.asyncio
    async def test_document_operations(self):
        """Test basic document operations"""
        config = DocPixieConfig(storage_type="memory")
        storage = InMemoryStorage(config)
        
        # Create test document
        pages = [
            Page(page_number=1, image_path="/test/page1.jpg"),
            Page(page_number=2, image_path="/test/page2.jpg")
        ]
        doc = Document(id="test-doc", name="Test Document", pages=pages)
        
        # Test save
        doc_id = await storage.save_document(doc)
        assert doc_id == "test-doc"
        
        # Test exists
        exists = await storage.document_exists("test-doc")
        assert exists is True
        
        # Test get
        retrieved_doc = await storage.get_document("test-doc")
        assert retrieved_doc is not None
        assert retrieved_doc.id == "test-doc"
        assert retrieved_doc.name == "Test Document"
        assert len(retrieved_doc.pages) == 2
        
        # Test list
        doc_list = await storage.list_documents()
        assert len(doc_list) == 1
        assert doc_list[0]['id'] == "test-doc"
        
        # Test delete
        deleted = await storage.delete_document("test-doc")
        assert deleted is True
        
        exists = await storage.document_exists("test-doc")
        assert exists is False


class TestProcessorFactory:
    """Test processor factory"""
    
    def test_factory_creation(self):
        """Test factory creation and extension mapping"""
        config = DocPixieConfig()
        factory = ProcessorFactory(config)
        
        extensions = factory.get_supported_extensions()
        assert '.pdf' in extensions
        assert '.jpg' in extensions
        assert '.png' in extensions
    
    def test_file_support(self):
        """Test file support detection"""
        config = DocPixieConfig()
        factory = ProcessorFactory(config)
        
        assert factory.supports_file("test.pdf") is True
        assert factory.supports_file("test.jpg") is True
        assert factory.supports_file("test.png") is True
        assert factory.supports_file("test.txt") is False
    
    def test_processor_selection(self):
        """Test processor selection"""
        config = DocPixieConfig()
        factory = ProcessorFactory(config)
        
        pdf_processor = factory.get_processor("test.pdf")
        assert pdf_processor.__class__.__name__ == "PDFProcessor"
        
        image_processor = factory.get_processor("test.jpg")
        assert image_processor.__class__.__name__ == "ImageProcessor"
        
        # Test unsupported file
        with pytest.raises(ValueError):
            factory.get_processor("test.txt")


class TestDocPixieAPI:
    """Test main DocPixie API"""
    
    def test_docpixie_creation(self):
        """Test DocPixie instance creation"""
        # Test with memory storage
        docpixie = create_memory_docpixie(provider="openai", api_key="test-key")
        
        assert docpixie.config.provider == "openai"
        assert docpixie.config.storage_type == "memory"
        assert isinstance(docpixie.storage, InMemoryStorage)
    
    def test_file_support(self):
        """Test file support checking"""
        docpixie = create_memory_docpixie(provider="openai", api_key="test-key")
        
        assert docpixie.supports_file("test.pdf") is True
        assert docpixie.supports_file("test.jpg") is True
        assert docpixie.supports_file("test.txt") is False
    
    def test_stats(self):
        """Test stats collection"""
        docpixie = create_memory_docpixie(provider="openai", api_key="test-key")
        
        stats = docpixie.get_stats()
        assert 'docpixie_version' in stats
        assert 'config' in stats
        assert 'storage' in stats
        assert 'supported_extensions' in stats
    
    @pytest.mark.asyncio
    async def test_placeholder_query(self):
        """Test placeholder query functionality (Phase 1)"""
        docpixie = create_memory_docpixie(provider="openai", api_key="test-key")
        
        # Add a test document to memory
        pages = [
            Page(page_number=1, image_path="/test/page1.jpg"),
            Page(page_number=2, image_path="/test/page2.jpg")
        ]
        doc = Document(id="test-doc", name="Test Document", pages=pages)
        await docpixie.storage.save_document(doc)
        
        # Test query (should return placeholder response)
        result = await docpixie.query("What is this document about?")
        
        assert result.query == "What is this document about?"
        assert "Phase 1 Placeholder" in result.answer
        assert len(result.selected_pages) > 0
        assert result.metadata['documents_searched'] == 1
        assert result.metadata['phase'] == 'Phase 1 - Basic functionality'


# Skip tests that require API keys if not available
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", 
        "requires_api_key: mark test as requiring API key"
    )


if __name__ == "__main__":
    # Run basic tests without pytest
    import asyncio
    
    async def run_basic_tests():
        print("Running basic DocPixie tests...")
        
        # Test configuration
        print("✓ Testing configuration")
        config = DocPixieConfig()
        assert config.provider == "openai"
        
        # Test models
        print("✓ Testing models")
        page = Page(page_number=1, image_path="/test.jpg")
        assert page.page_number == 1
        
        # Test storage
        print("✓ Testing storage")
        storage = InMemoryStorage(config)
        assert storage.get_document_count() == 0
        
        # Test DocPixie API
        print("✓ Testing DocPixie API")
        docpixie = create_memory_docpixie(provider="openai", api_key="test-key")
        assert docpixie.supports_file("test.pdf") is True
        
        print("All basic tests passed! ✓")
    
    asyncio.run(run_basic_tests())