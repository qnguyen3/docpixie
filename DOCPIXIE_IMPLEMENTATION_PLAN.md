# DocPixie Open-Source Implementation Plan (Revised)

## Overview
Transform the production DocPixie backend into a simplified open-source library that maintains Flash and Pro modes while removing embedding/vector database dependencies. All retrieval will be vision-based using a two-stage approach.

## Core Changes from Production
- **Remove**: Embeddings, Milvus vector database, Jina API
- **Keep**: Flash/Pro mode distinction for different complexity levels
- **Change**: PDF processing from pdf2image to PyMuPDF (faster, better quality)
- **New**: Vision-based page selection replacing vector search

---

## Phase 1: Core Foundation (Week 1-2) ✅ **COMPLETED**
**Goal**: Basic document processing and storage without embeddings

### Components to Build

#### 1.1 Document Processing with PyMuPDF
**Replace**: `app/utils/document_utils.py` PDF processing
```python
# New implementation with PyMuPDF
docpixie/processors/
├── base.py         # Abstract processor
├── pdf.py          # PyMuPDF implementation (NEW)
├── image.py        # Image processor
└── factory.py      # Processor selection
```

**PyMuPDF Benefits**:
- Faster rendering (3-5x faster than pdf2image)
- Better text extraction
- Direct image extraction
- No external dependencies (no poppler)

**Implementation**:
```python
# processors/pdf.py
import fitz  # PyMuPDF

class PDFProcessor:
    def process(self, file_path):
        doc = fitz.open(file_path)
        pages = []
        for page_num, page in enumerate(doc):
            # Render page to image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale
            img_data = pix.pil_tobytes(format="JPEG")
            pages.append(img_data)
        return pages
```

#### 1.2 Storage Layer (Simplify Existing)
**Reuse from**: `app/utils/local_storage.py`
```python
# Simplify for no embeddings
docpixie/storage/
├── base.py         # Abstract interface
├── local.py        # File system storage
└── memory.py       # In-memory for testing
```

#### 1.3 Document Models
**Adapt from**: `app/models/schemas.py`
```python
# Keep Flash/Pro distinction
@dataclass
class QueryMode(Enum):
    FLASH = "flash"  # Quick, simple queries
    PRO = "pro"      # Complex, multi-step analysis

@dataclass
class Document:
    id: str
    name: str
    pages: List[Page]
    summary: Optional[str]
    page_summaries: List[str]  # For vision-based selection
```

### Deliverables
- [x] PyMuPDF document processing
- [x] Page image optimization
- [x] Local storage implementation
- [x] Document summary generation (with all pages in single vision call)
- [x] Unit tests for processors

### Code Migration
```
✓ Remove: pdf2image dependency
✓ Add: PyMuPDF for PDF processing
✓ Keep: Image optimization logic
✓ Simplify: Storage without embeddings
✓ Provider refactoring: Clean API separation
✓ Document summary: All pages in single vision call
```

---

## Phase 2: Vision-Based RAG Pipeline (Week 3-4)
**Goal**: Implement Flash and Pro modes without embeddings

### Components to Build

#### 2.1 Flash Mode Handler (Simplify)
**Adapt from**: `app/core/rag/flash_handler.py`
```python
# Simplified Flash mode
class FlashHandler:
    async def process_query(self, query, documents):
        # 1. Vision-based page selection (quick)
        selected_pages = await self.select_pages_flash(
            query, 
            all_pages,
            max_pages=5  # Fewer pages for speed
        )
        
        # 2. Generate answer
        answer = await self.generate_answer(query, selected_pages)
        return answer
```

**Flash Mode Characteristics**:
- Faster response (5-10 seconds)
- Fewer pages analyzed (max 5)
- Single-pass selection
- Lower detail vision analysis

#### 2.2 Pro Mode Handler (Simplify)
**Adapt from**: `app/core/rag/pro_handler.py`
```python
# Simplified Pro mode - No task planner, but multi-step
class ProHandler:
    async def process_query(self, query, documents):
        # 1. Comprehensive page selection
        relevant_pages = await self.select_pages_pro(
            query,
            all_pages, 
            max_pages=15  # More pages for thoroughness
        )
        
        # 2. Multi-step analysis
        analyses = []
        for aspect in self.identify_query_aspects(query):
            analysis = await self.analyze_aspect(aspect, relevant_pages)
            analyses.append(analysis)
        
        # 3. Synthesize comprehensive answer
        answer = await self.synthesize(query, analyses)
        return answer
```

**Pro Mode Characteristics**:
- Thorough analysis (20-30 seconds)
- More pages analyzed (max 15)
- Multi-aspect investigation
- High detail vision analysis
- Synthesis step for comprehensive answers

#### 2.3 Vision-Based Page Selection
**New Implementation**:
```python
# Two different selection strategies

async def select_pages_flash(query, pages, max_pages=5):
    """Quick selection using thumbnails"""
    # Use low-detail mode for speed
    # Single prompt to select most relevant pages
    
async def select_pages_pro(query, pages, max_pages=15):
    """Thorough selection with summaries"""
    # Use page summaries + thumbnails
    # May do multiple rounds of selection
    # Group related pages together
```

### Deliverables
- [ ] Flash mode implementation
- [ ] Pro mode implementation
- [ ] Vision-based page selection
- [ ] Mode selection logic
- [ ] Integration tests

### Code Migration
```
✓ Keep: Flash/Pro mode structure
✓ Simplify: Remove task planner
✓ Replace: Vector search with vision selection
✓ Keep: Synthesis for Pro mode
```

---

## Phase 3: Orchestration & API (Week 5-6)
**Goal**: Clean API maintaining Flash/Pro distinction

### Components to Build

#### 3.1 Orchestrator (Adapt)
**Simplify from**: `app/core/rag/orchestrator.py`
```python
class Orchestrator:
    def __init__(self):
        self.flash_handler = FlashHandler()
        self.pro_handler = ProHandler()
    
    async def query(self, question, mode="auto", **kwargs):
        # Auto mode selection based on query complexity
        if mode == "auto":
            mode = self.determine_mode(question)
        
        if mode == "flash":
            return await self.flash_handler.process_query(question, **kwargs)
        else:
            return await self.pro_handler.process_query(question, **kwargs)
    
    def determine_mode(self, question):
        # Simple heuristics for mode selection
        indicators_pro = [
            "compare", "analyze", "explain in detail",
            "comprehensive", "all aspects", "thorough"
        ]
        if any(ind in question.lower() for ind in indicators_pro):
            return "pro"
        return "flash"
```

#### 3.2 Main API Class
```python
class DocPixie:
    async def query(
        self,
        question: str,
        mode: Literal["flash", "pro", "auto"] = "auto",
        stream: bool = False
    ):
        """
        Query with mode selection
        
        Args:
            question: User question
            mode: Flash (quick), Pro (thorough), or Auto
            stream: Stream response
        """
        return await self.orchestrator.query(
            question, 
            mode=mode,
            stream=stream
        )
```

#### 3.3 Configuration
```python
@dataclass
class DocPixieConfig:
    # Mode-specific settings
    flash_max_pages: int = 5
    flash_vision_detail: str = "low"
    flash_timeout: int = 10
    
    pro_max_pages: int = 15
    pro_vision_detail: str = "high"
    pro_timeout: int = 30
    pro_synthesis_enabled: bool = True
    
    # PyMuPDF settings
    pdf_render_scale: float = 2.0
    pdf_max_image_size: tuple = (2048, 2048)
```

### Deliverables
- [ ] Orchestrator with mode selection
- [ ] Main API class
- [ ] Auto mode detection
- [ ] Configuration system
- [ ] Usage examples for both modes

---

## Phase 4: Provider Support (Week 7-8) ✅ **COMPLETED**  
**Goal**: Multiple vision providers with mode support

### Components to Build

#### 4.1 Provider Interface (Updated Architecture)
```python
# Clean separation: Providers handle raw API calls only
class BaseProvider(ABC):
    @abstractmethod
    async def process_text_messages(
        self, 
        messages: List[dict], 
        max_tokens: int = 300, 
        temperature: float = 0.3
    ) -> str:
        """Process text-only messages through provider API"""
        
    @abstractmethod
    async def process_multimodal_messages(
        self, 
        messages: List[dict], 
        max_tokens: int = 300, 
        temperature: float = 0.3
    ) -> str:
        """Process messages with text and images through provider API"""

# Business logic handled in AI operations layer
class PageSelector:
    """Handles page selection business logic for Flash/Pro modes"""
    
    def __init__(self, provider: BaseProvider, config: DocPixieConfig):
        self.provider = provider
        self.config = config
    
    async def select_pages_flash(self, query, pages, max_pages=5):
        """Quick selection using provider with low-detail prompts"""
        # Build Flash mode selection messages
        messages = self._build_flash_selection_messages(query, pages, max_pages)
        
        # Use provider for raw API call
        result = await self.provider.process_multimodal_messages(
            messages=messages,
            max_tokens=100,
            temperature=0.1
        )
        
        return self._parse_selection_result(result, pages)
        
    async def select_pages_pro(self, query, pages, max_pages=15):
        """Thorough selection using provider with high-detail analysis"""
        # Build Pro mode selection messages with summaries
        messages = self._build_pro_selection_messages(query, pages, max_pages)
        
        # Use provider for raw API call
        result = await self.provider.process_multimodal_messages(
            messages=messages,
            max_tokens=200,
            temperature=0.1
        )
        
        return self._parse_selection_result(result, pages)
```

#### 4.2 OpenAI Provider (Updated)
```python
class OpenAIProvider(BaseProvider):
    """OpenAI provider for raw API operations only"""
    
    def __init__(self, config: DocPixieConfig):
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.model = config.vision_model
    
    async def process_text_messages(self, messages, max_tokens=300, temperature=0.3):
        """Process text-only messages through OpenAI API"""
        response = await self.client.chat.completions.create(
            model=self.config.pro_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
    
    async def process_multimodal_messages(self, messages, max_tokens=300, temperature=0.3):
        """Process multimodal messages through OpenAI Vision API"""
        # Convert image_path type to OpenAI format
        processed_messages = self._prepare_openai_messages(messages)
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=processed_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content.strip()
```

#### 4.3 Anthropic Provider (Updated)
```python
class AnthropicProvider(BaseProvider):
    """Anthropic provider for raw API operations only"""
    
    def __init__(self, config: DocPixieConfig):
        self.client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
        self.model = config.vision_model  # Use vision model for multimodal operations
    
    async def process_text_messages(self, messages, max_tokens=300, temperature=0.3):
        """Process text-only messages through Anthropic API"""
        claude_messages = self._prepare_claude_text_messages(messages)
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=claude_messages
        )
        return response.content[0].text.strip()
    
    async def process_multimodal_messages(self, messages, max_tokens=300, temperature=0.3):
        """Process multimodal messages through Anthropic Vision API"""
        # Convert image_path type to Claude format (base64)
        claude_messages = self._prepare_claude_multimodal_messages(messages)
        
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=claude_messages
        )
        return response.content[0].text.strip()
```

### Deliverables
- [x] Clean provider abstraction (BaseProvider)
- [x] OpenAI implementation (raw API only)
- [x] Anthropic implementation (raw API only)  
- [x] AI operations layer (PageSelector, Summarizer, etc.)
- [ ] Provider benchmarks
- [ ] Cost comparison guide

---

## Phase 5: Advanced Features (Week 9-10)
**Goal**: Production optimizations

### Components to Build

#### 5.1 Query Preprocessing
**Adapt from**: `app/core/query_reformulator.py`
```python
# Simplified version for open source
class QueryPreprocessor:
    def preprocess(self, query, mode):
        if mode == "flash":
            # Basic expansion
            return self.expand_abbreviations(query)
        else:  # pro
            # More sophisticated preprocessing
            return self.identify_aspects(query)
```

#### 5.2 Caching System
```python
class CacheMiddleware:
    def __init__(self):
        self.page_summary_cache = {}  # Cache summaries
        self.selection_cache = {}     # Cache page selections
        self.answer_cache = LRU(100)  # Cache recent answers
```

#### 5.3 Batch Processing
```python
class BatchProcessor:
    async def process_documents(self, file_paths, callback=None):
        # Parallel document processing with PyMuPDF
        # Progress callbacks
        # Error handling per document
```

#### 5.4 Streaming Responses
```python
# Different streaming for Flash vs Pro
async def stream_flash(query, pages):
    # Single stream of answer
    
async def stream_pro(query, pages):
    # Stream with status updates
    # "Analyzing aspect 1/3..."
    # "Synthesizing findings..."
```

### Deliverables
- [ ] Query preprocessing
- [ ] Caching layer
- [ ] Batch document processing
- [ ] Enhanced streaming
- [ ] Performance optimizations

---

## Phase 6: Storage & Deployment (Week 11)
**Goal**: Cloud storage and deployment readiness

### Components to Build

#### 6.1 Cloud Storage
```python
# S3 Storage with presigned URLs
class S3Storage(BaseStorage):
    async def save_page_image(self, page_image):
        # Upload to S3
        # Return presigned URL for vision API
```

#### 6.2 Async Optimization
```python
# Optimize for different modes
class AsyncOptimizer:
    async def optimize_flash(self):
        # Prioritize speed
        # Smaller images, lower quality
        
    async def optimize_pro(self):
        # Prioritize quality
        # Full resolution, multiple passes
```

### Deliverables
- [ ] S3 storage implementation
- [ ] Azure storage implementation
- [ ] Deployment guides
- [ ] Docker support

---

## Phase 7: Documentation & Release (Week 12)
**Goal**: Production-ready release

### Documentation Structure
```
docs/
├── getting-started/
│   ├── installation.md
│   ├── quickstart.md
│   └── flash-vs-pro.md
├── guides/
│   ├── choosing-modes.md
│   ├── provider-selection.md
│   └── optimization.md
├── api-reference/
│   ├── docpixie.md
│   ├── providers.md
│   └── storage.md
└── examples/
    ├── flash-mode-examples.py
    ├── pro-mode-examples.py
    └── custom-provider.py
```

### Testing Strategy
- Unit tests for each component
- Integration tests for both modes
- Performance benchmarks (Flash vs Pro)
- Cost analysis per mode

### Release Checklist
- [ ] PyPI package configuration
- [ ] GitHub Actions CI/CD
- [ ] Example applications
- [ ] Migration guide from production
- [ ] Demo video showing both modes

---

## Implementation Timeline

### Weeks 1-2: Foundation with PyMuPDF ✅ **COMPLETED**
```python
# Priority: Get PyMuPDF working
✓ Set up PyMuPDF processing
✓ Test PDF rendering quality
✓ Optimize image generation
✓ Create page summaries
✓ Provider architecture refactoring
✓ Document summary with all pages in single call
```

### Weeks 3-4: Dual Mode RAG
```python
# Priority: Flash and Pro modes working
- Implement Flash handler
- Implement Pro handler
- Vision-based selection
- Test mode differences
```

### Weeks 5-6: API & Orchestration
```python
# Priority: Clean API
- Mode auto-selection
- Streaming for both modes
- Configuration system
```

### Weeks 7-8: Multiple Providers ✅ **COMPLETED**
```python
# Priority: Provider abstraction
✓ OpenAI support
✓ Anthropic support
✓ Clean provider abstraction (BaseProvider)
✓ AI operations layer separation
- Provider comparison
```

### Weeks 9-10: Optimization
```python
# Priority: Performance
- Caching
- Batch processing
- Query preprocessing
```

### Weeks 11-12: Polish & Release
```python
# Priority: Release ready
- Documentation
- Examples
- PyPI release
```

---

## Key Differences from Production

| Component | Production | Open Source |
|-----------|------------|-------------|
| PDF Processing | pdf2image | PyMuPDF |
| Page Selection | Vector search | Vision-based |
| Embeddings | Jina API | None |
| Vector DB | Milvus | None |
| Flash Mode | Vector retrieval | Vision selection (fast) |
| Pro Mode | Task planner + Vector | Vision selection (thorough) |
| Storage | Supabase | Local/S3/Azure |

---

## Success Metrics

### Flash Mode Success
- [ ] Response time < 10 seconds
- [ ] Accurate for simple queries
- [ ] Cost < $0.05 per query

### Pro Mode Success
- [ ] Response time < 30 seconds
- [ ] Comprehensive analysis
- [ ] Handles complex queries
- [ ] Cost < $0.20 per query

### Overall Success
- [ ] Easy to install (`pip install docpixie`)
- [ ] Works out of the box
- [ ] Clear mode distinction
- [ ] Good documentation
- [ ] Active community

---

## Risk Mitigation

### Technical Risks
1. **PyMuPDF compatibility**: Test across platforms
2. **Vision API costs**: Implement aggressive caching
3. **Mode selection accuracy**: Allow manual override

### Performance Risks
1. **Flash mode too slow**: Optimize image sizes
2. **Pro mode too expensive**: Implement page limits
3. **Memory usage**: Stream processing, cleanup

---

## Code Reuse Summary

### Keep with Modifications
- Flash/Pro handler structure → Remove embeddings
- Orchestrator pattern → Simplify pipeline
- Vision analysis code → Enhance for selection
- Storage abstractions → Remove vector refs

### Replace Completely
- pdf2image → PyMuPDF
- Vector search → Vision selection
- Embedding generation → Page summaries
- Milvus operations → Direct storage

### New Components
- Vision-based page selector
- Mode auto-detection
- PyMuPDF processor
- Simplified synthesis

---

## Progress Summary

### ✅ Completed Components
1. **Foundation** (Phase 1): PyMuPDF processing, storage, document models, summarization
2. **Provider Architecture** (Phase 4): Clean separation between API providers and business logic
3. **Core Infrastructure**: Configuration system, document/page models, unit tests

### 🚧 Next Steps (Current Priority)
1. **Phase 2**: Implement Flash and Pro modes with vision-based page selection
2. **Phase 3**: Build orchestrator and main API with mode auto-detection
3. **Integration Testing**: Test complete pipeline with both providers

This revised plan maintains the Flash/Pro distinction while eliminating embeddings, uses PyMuPDF for better PDF processing, and provides a clear path from the existing codebase to the simplified open-source version.