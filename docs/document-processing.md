# Document Processing in DocPixie

DocPixie's core philosophy is simple: **Everything becomes an image**. This vision-first approach preserves layout, formatting, charts, and visual elements that text extraction would lose.

## How Document Processing Works

### The DocPixie Pipeline

```
Input File → Format Detection → Image Conversion → Page Storage → Summary Generation
    │              │                  │                │              │
    PDF         Auto-detect      PyMuPDF/PIL      Local/S3       Vision Model
   Image         Extension         JPEG             Storage       Analysis
   PPTX        → PDF → Image     Optimization
```

### Core Processing Steps

1. **Format Detection**: Identifies file type by extension
2. **Conversion**: Transforms document to high-quality images
3. **Optimization**: Resizes and compresses for optimal API usage
4. **Storage**: Saves processed pages for retrieval
5. **Summarization**: Vision model analyzes all pages together

## Supported Formats

### Native Support

- **PDF** (.pdf) - Direct processing with PyMuPDF
- **Images** (.png, .jpg, .jpeg, .webp) - Direct optimization
- **More coming** - DOCX, XLSX in development

### Extended Support (via PDF conversion)

Any format that can be converted to PDF can work with DocPixie. Here's how to handle PowerPoint files:

## Processing PowerPoint Files (PPTX)

Since DocPixie is vision-native, we convert PPTX to PDF first, then let DocPixie's built-in PyMuPDF processor handle the PDF→Images conversion. This preserves all visual elements, animations frames, and formatting.

### Installation

```bash
# PyMuPDF is already included with DocPixie for PDF processing
# Just need LibreOffice for PPTX → PDF conversion

# macOS:
brew install libreoffice

# Ubuntu/Debian:
sudo apt-get install libreoffice

# Windows:
# Download from https://www.libreoffice.org/download/
```

### PPTX Processor Implementation

Since DocPixie already uses PyMuPDF for PDF processing, we'll leverage it for the entire pipeline after converting PPTX to PDF:

```python
# pptx_processor.py
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from docpixie import create_docpixie
from docpixie.models.document import Document

class PPTXProcessor:
    """Convert PPTX to PDF for DocPixie processing"""
    
    def __init__(self, pixie):
        self.pixie = pixie
        self.temp_dir = tempfile.mkdtemp(prefix="pptx_")
    
    def process_pptx(
        self, 
        pptx_path: str,
        document_name: Optional[str] = None
    ) -> Document:
        """
        Process a PowerPoint file through DocPixie
        
        The pipeline:
        1. PPTX → PDF (using LibreOffice)
        2. PDF → Images (using PyMuPDF via DocPixie)
        3. Images → Document with AI summary
        
        Args:
            pptx_path: Path to PPTX file
            document_name: Optional custom name
            
        Returns:
            Processed Document object
        """
        # Validate input
        if not Path(pptx_path).exists():
            raise FileNotFoundError(f"File not found: {pptx_path}")
        
        if not pptx_path.lower().endswith('.pptx'):
            raise ValueError("File must be a .pptx file")
        
        # Step 1: Convert PPTX to PDF using LibreOffice
        pdf_path = self._convert_to_pdf(pptx_path)
        
        try:
            # Step 2: Process PDF with DocPixie (uses PyMuPDF internally)
            # This automatically:
            # - Converts PDF pages to images using PyMuPDF
            # - Optimizes images for vision model processing
            # - Generates AI summary of all slides
            
            if not document_name:
                document_name = Path(pptx_path).stem
            
            document = self.pixie.add_document_sync(
                pdf_path,
                document_name=document_name
            )
            
            print(f"✓ Processed {document.page_count} slides from {document_name}")
            return document
            
        finally:
            # Clean up temporary PDF
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
    
    def _convert_to_pdf(self, pptx_path: str) -> str:
        """Convert PPTX to PDF using LibreOffice"""
        
        # Output PDF path
        pdf_name = Path(pptx_path).stem + ".pdf"
        pdf_path = os.path.join(self.temp_dir, pdf_name)
        
        # LibreOffice conversion command
        cmd = [
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', self.temp_dir,
            pptx_path
        ]
        
        try:
            # Run conversion
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Conversion failed: {result.stderr}")
            
            if not os.path.exists(pdf_path):
                raise RuntimeError("PDF was not created")
            
            return pdf_path
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Conversion timed out")
        except FileNotFoundError:
            raise RuntimeError(
                "LibreOffice not found. Please install it:\n"
                "  macOS: brew install libreoffice\n"
                "  Linux: sudo apt-get install libreoffice\n"
                "  Windows: Download from libreoffice.org"
            )
    
    def __del__(self):
        """Clean up temp directory"""
        import shutil
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
```

### Using the PPTX Processor

```python
from docpixie import create_docpixie

# Initialize DocPixie
pixie = create_docpixie(provider="openai")

# Create PPTX processor
pptx_processor = PPTXProcessor(pixie)

# Process a presentation
document = pptx_processor.process_pptx(
    "company_presentation.pptx",
    document_name="Q4 Company Update"
)

# Now query the presentation
result = pixie.query_sync(
    "What are the key revenue figures shown in the presentation?"
)

print(result.answer)
print(f"Information from slides: {result.page_numbers}")
```

### Alternative: Direct PPTX to PDF with python-pptx2pdf

If LibreOffice is not available, you can use python-pptx2pdf (Windows/macOS only):

```python
# Alternative PPTX to PDF converter
# Install: pip install pptx2pdf

from pptx2pdf import convert
import tempfile
import os

class SimplePPTXProcessor:
    """Alternative PPTX processor using pptx2pdf"""
    
    def __init__(self, pixie):
        self.pixie = pixie
    
    def process_pptx(self, pptx_path: str, document_name: Optional[str] = None) -> Document:
        """
        Process PPTX using pptx2pdf library
        Note: Only works on Windows and macOS with PowerPoint installed
        """
        # Create temp PDF
        temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_pdf_path = temp_pdf.name
        temp_pdf.close()
        
        try:
            # Convert PPTX to PDF
            convert(pptx_path, temp_pdf_path)
            
            # Let DocPixie process the PDF (PyMuPDF handles PDF→Images)
            document = self.pixie.add_document_sync(
                temp_pdf_path,
                document_name=document_name or Path(pptx_path).stem
            )
            
            return document
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)

# Note: LibreOffice method is recommended as it works on all platforms
# and doesn't require Microsoft PowerPoint to be installed
```

## Processing Other Document Types

### Word Documents (DOCX)

```python
# Install: pip install python-docx pypandoc
import pypandoc
import tempfile

def process_docx(docx_path: str, pixie):
    """Convert DOCX to PDF then process with DocPixie"""
    
    # Convert DOCX to PDF using pypandoc
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        pypandoc.convert_file(
            docx_path,
            'pdf',
            outputfile=tmp.name
        )
        
        # Process with DocPixie
        document = pixie.add_document_sync(tmp.name)
        
    return document
```

### Excel Files (XLSX)

```python
# Install: pip install openpyxl pandas matplotlib
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def process_excel(xlsx_path: str, pixie):
    """Convert Excel sheets to images for DocPixie"""
    
    # Read Excel file
    excel_file = pd.ExcelFile(xlsx_path)
    temp_dir = Path("temp_excel")
    temp_dir.mkdir(exist_ok=True)
    
    # Convert each sheet to image
    for sheet_name in excel_file.sheet_names:
        df = excel_file.parse(sheet_name)
        
        # Create visualization
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.axis('tight')
        ax.axis('off')
        
        # Render dataframe as table
        table = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            cellLoc='center',
            loc='center'
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        
        # Save as image
        img_path = temp_dir / f"{sheet_name}.png"
        plt.savefig(img_path, bbox_inches='tight', dpi=150)
        plt.close()
    
    # Create PDF from images and process
    # ... (combine images to PDF, then use DocPixie)
```

## Image Optimization Settings

DocPixie automatically optimizes images for vision model processing:

```python
from docpixie.core.config import DocPixieConfig

config = DocPixieConfig(
    # Image quality settings
    jpeg_quality=90,              # 1-100, higher = better quality
    pdf_render_scale=2.0,         # Scale factor for PDF rendering
    pdf_max_image_size=(2048, 2048),  # Max dimensions
    
    # Vision model settings
    vision_detail="high",         # "high" or "auto"
)
```

### Optimization Guidelines

| Document Type | Recommended Settings | Notes |
|--------------|---------------------|-------|
| Text-heavy PDFs | `jpeg_quality=85`, `scale=1.5` | Balance quality and size |
| Presentations | `jpeg_quality=90`, `scale=2.0` | Preserve visual elements |
| Technical diagrams | `jpeg_quality=95`, `scale=2.5` | Maximum clarity |
| Scanned documents | `jpeg_quality=90`, `scale=2.0` | OCR quality important |

## Custom Processors

Create custom processors for any document type:

```python
from docpixie.processors.base import BaseProcessor
from docpixie.models.document import Document, Page
import asyncio

class CustomProcessor(BaseProcessor):
    """Template for custom document processors"""
    
    SUPPORTED_EXTENSIONS = ['.custom']
    
    async def process(
        self, 
        file_path: str, 
        document_id: Optional[str] = None
    ) -> Document:
        """
        Convert your format to images
        
        Steps:
        1. Read your custom format
        2. Convert to images (JPEG/PNG)
        3. Create Page objects
        4. Return Document
        """
        
        # Your conversion logic here
        images = self.convert_to_images(file_path)
        
        # Create pages
        pages = []
        for i, img_path in enumerate(images, 1):
            page = Page(
                page_number=i,
                image_path=img_path,
                metadata={'source_format': 'custom'}
            )
            pages.append(page)
        
        # Create document
        return Document(
            id=document_id or str(uuid.uuid4()),
            name=Path(file_path).stem,
            pages=pages
        )
    
    def convert_to_images(self, file_path: str) -> List[str]:
        """Your custom conversion logic"""
        # Implement format-specific conversion
        pass
```

## Performance Considerations

### Processing Speed

| Format | Pages | Typical Time | Notes |
|--------|-------|--------------|-------|
| PDF | 10 | 2-3 seconds | PyMuPDF is fast |
| PDF | 100 | 15-20 seconds | Includes optimization |
| PPTX | 30 | 5-8 seconds | LibreOffice conversion |
| Images | 10 | 1-2 seconds | Just optimization |

### Memory Usage

- Each page image: ~200-500KB (optimized)
- Processing buffer: ~50MB per 10 pages
- Storage: ~5MB per document (10 pages)

### Best Practices

1. **Batch Processing**: Process multiple documents asynchronously
2. **Image Quality**: Balance quality vs. API costs
3. **Page Limits**: Set reasonable limits for large documents
4. **Cleanup**: Remove temporary files after processing

## Troubleshooting

### Common Issues

**"Failed to process PDF"**
```python
# Check PDF validity
import fitz
try:
    doc = fitz.open("document.pdf")
    print(f"Valid PDF with {doc.page_count} pages")
    doc.close()
except:
    print("Invalid or corrupted PDF")
```

**"PPTX conversion failed"**
```bash
# Verify LibreOffice installation
libreoffice --version

# Test conversion manually
libreoffice --headless --convert-to pdf presentation.pptx
```

**"Out of memory"**
```python
# Process large documents in chunks
config = DocPixieConfig(
    pdf_render_scale=1.5,  # Reduce scale
    jpeg_quality=85,       # Reduce quality
    pdf_max_image_size=(1536, 1536)  # Smaller max size
)
```

## Next Steps

- Learn about [Storage Options](storage.md) for managing processed documents
- Explore [Data Models](models.md) to understand document structure
- Check [Getting Started](getting-started.md) for usage examples