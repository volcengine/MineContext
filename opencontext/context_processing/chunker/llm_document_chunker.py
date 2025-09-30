#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

"""
Intelligent Document Chunker based on LLM
Uses large language models to understand document structure and perform intelligent chunking
"""

import json
import re
from typing import List, Dict, Any, Optional, Iterator, Tuple
from pathlib import Path
from abc import ABC, abstractmethod

import pypdf

from opencontext.context_processing.chunker.chunkers import BaseChunker, ChunkingConfig
from opencontext.models.context import RawContextProperties, Chunk
from opencontext.llm.global_vlm_client import generate_with_messages
from opencontext.utils.logging_utils import get_logger

logger = get_logger(__name__)


class DocumentExtractor(ABC):
    """Base class for document content extractors"""
    
    @abstractmethod
    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract document content and structure information
        
        Args:
            file_path: Document path
            
        Returns:
            Dict containing content, metadata, structure information
        """
        pass


class EnhancedPDFExtractor(DocumentExtractor):
    """Enhanced PDF document extractor - Supports extraction of images, tables and location information"""
    
    def extract(self, file_path: str) -> Dict[str, Any]:
        """Extract PDF content including text, images, tables and structure information"""
        try:
            import base64
            with open(file_path, 'rb') as file:
                pdf = pypdf.PdfReader(file)
                content = ""
                pages_info = []
                all_images = []
                all_tables = []
                
                for i, page in enumerate(pdf.pages):
                    page_content = f"\n--- Page {i+1} ---\n"
                    
                    # Extract text content
                    page_text = page.extract_text()
                    
                    # Extract images from page
                    page_images = self._extract_images_from_page(page, i + 1)
                    all_images.extend(page_images)
                    
                    # Insert image placeholders in text
                    for img in page_images:
                        page_text += f"\n[IMAGE:{img['id']}]\n"
                    
                    # Extract tables (simple table detection)
                    page_tables = self._detect_tables_in_text(page_text, i + 1)
                    all_tables.extend(page_tables)
                    
                    # Insert table placeholders in text
                    for table in page_tables:
                        page_text = page_text.replace(table['original_text'], f"[TABLE:{table['id']}]")
                    
                    page_content += page_text
                    content += page_content
                    
                    # Record page information
                    pages_info.append({
                        'page': i + 1,
                        'text_length': len(page_text),
                        'start_position': len(content) - len(page_content),
                        'end_position': len(content),
                        'images_count': len(page_images),
                        'tables_count': len(page_tables)
                    })
                
                return {
                    'content': content.strip(),
                    'metadata': {
                        'total_pages': len(pdf.pages),
                        'title': pdf.metadata.get('/Title', '') if pdf.metadata else '',
                        'author': pdf.metadata.get('/Author', '') if pdf.metadata else '',
                        'creator': pdf.metadata.get('/Creator', '') if pdf.metadata else '',
                        'total_images': len(all_images),
                        'total_tables': len(all_tables)
                    },
                    'structure': {
                        'pages': pages_info,
                        'images': all_images,
                        'tables': all_tables,
                        'type': 'pdf'
                    }
                }
        except Exception as e:
            logger.exception(f"Failed to extract PDF content: {e}")
            raise
    
    def _extract_images_from_page(self, page, page_num: int) -> List[Dict]:
        """Extract images from PDF page"""
        images = []
        try:
            if '/XObject' in page['/Resources']:
                xobjects = page['/Resources']['/XObject'].get_object()
                img_count = 0
                
                for obj_name in xobjects:
                    obj = xobjects[obj_name]
                    if obj['/Subtype'] == '/Image':
                        img_count += 1
                        img_id = f"img_{page_num}_{img_count}"
                        
                        # Extract image data
                        try:
                            import base64
                            img_data = obj._data
                            img_base64 = base64.b64encode(img_data).decode('utf-8')
                            
                            images.append({
                                'id': img_id,
                                'page': page_num,
                                'name': str(obj_name),
                                'width': obj.get('/Width', 0),
                                'height': obj.get('/Height', 0),
                                'base64': img_base64,
                                'size': len(img_data),
                                'format': obj.get('/Filter', 'unknown')
                            })
                        except Exception as e:
                            logger.debug(f"Failed to extract image {obj_name}: {e}")
                            
        except Exception as e:
            logger.debug(f"Page {page_num} image extraction failed: {e}")
            
        return images
    
    def _detect_tables_in_text(self, text: str, page_num: int) -> List[Dict]:
        """Detect table structures in text"""
        tables = []
        try:
            lines = text.split('\n')
            table_count = 0
            current_table = []
            in_table = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    if in_table and current_table:
                        # Table ends
                        table_count += 1
                        table_id = f"table_{page_num}_{table_count}"
                        table_text = '\n'.join(current_table)
                        
                        tables.append({
                            'id': table_id,
                            'page': page_num,
                            'rows': len(current_table),
                            'original_text': table_text,
                            'content': self._parse_table_content(current_table)
                        })
                        
                        current_table = []
                        in_table = False
                    continue
                
                # Simple table detection: lines containing multiple separators
                if self._looks_like_table_row(line):
                    in_table = True
                    current_table.append(line)
                elif in_table:
                    # Possibly a continuation line of the table
                    current_table.append(line)
            
            # Handle table at end of document
            if in_table and current_table:
                table_count += 1
                table_id = f"table_{page_num}_{table_count}"
                table_text = '\n'.join(current_table)
                
                tables.append({
                    'id': table_id,
                    'page': page_num,
                    'rows': len(current_table),
                    'original_text': table_text,
                    'content': self._parse_table_content(current_table)
                })
                
        except Exception as e:
            logger.debug(f"Page {page_num} table detection failed: {e}")
            
        return tables
    
    def _looks_like_table_row(self, line: str) -> bool:
        """Determine if a line of text looks like a table row"""
        # Check if it contains multiple separators
        separators = ['\t', '|', '  ', ' - ']
        for sep in separators:
            if line.count(sep) >= 2:
                return True
        return False
    
    def _parse_table_content(self, table_lines: List[str]) -> List[List[str]]:
        """Parse table content into structured data"""
        try:
            parsed_rows = []
            for line in table_lines:
                # Try different separators
                if '\t' in line:
                    cells = line.split('\t')
                elif '|' in line:
                    cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                else:
                    # Split by multiple spaces
                    cells = re.split(r'\s{2,}', line)
                
                if cells:
                    parsed_rows.append([cell.strip() for cell in cells])
            
            return parsed_rows
        except Exception as e:
            logger.debug(f"Failed to parse table content: {e}")
            return []


class ReStructuredTextExtractor(DocumentExtractor):
    """ReStructuredText document extractor"""
    
    def extract(self, file_path: str) -> Dict[str, Any]:
        """Extract RST content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Parse RST title hierarchy
            headers = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if i > 0 and line.strip() and set(line.strip()) <= {'=', '-', '~', '^', '"', "'"}:
                    # RST title underline
                    if i - 1 >= 0:
                        title = lines[i-1].strip()
                        if title:
                            char = line.strip()[0] if line.strip() else '='
                            level = {'=': 1, '-': 2, '~': 3, '^': 4, '"': 5, "'": 6}.get(char, 1)
                            headers.append({
                                'level': level,
                                'title': title,
                                'line': i,
                                'position': sum(len(l) + 1 for l in lines[:i-1])
                            })
                
            return {
                'content': content,
                'metadata': {
                    'total_lines': len(lines),
                    'title': headers[0]['title'] if headers else Path(file_path).stem,
                    'format': 'rst'
                },
                'structure': {
                    'headers': headers,
                    'type': 'rst'
                }
            }
        except Exception as e:
            logger.exception(f"RST content extraction failed: {e}")
            raise


class HtmlExtractor(DocumentExtractor):
    """HTML document extractor"""
    
    def extract(self, file_path: str) -> Dict[str, Any]:
        """Extract HTML content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            # Simple HTML parsing, extract text content
            import re
            
            # Remove script and style tags
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Extract title
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else Path(file_path).stem
            
            # Extract heading tags
            headers = []
            for i, match in enumerate(re.finditer(r'<h([1-6])[^>]*>(.*?)</h[1-6]>', html_content, re.IGNORECASE | re.DOTALL)):
                level = int(match.group(1))
                header_text = re.sub(r'<[^>]+>', '', match.group(2)).strip()
                headers.append({
                    'level': level,
                    'title': header_text,
                    'position': match.start()
                })
            
            # Remove all HTML tags, keep text
            clean_text = re.sub(r'<[^>]+>', ' ', html_content)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            return {
                'content': clean_text,
                'metadata': {
                    'title': title,
                    'format': 'html',
                    'original_length': len(html_content)
                },
                'structure': {
                    'headers': headers,
                    'type': 'html'
                }
            }
        except Exception as e:
            logger.exception(f"HTML content extraction failed: {e}")
            raise


class ImageExtractor(DocumentExtractor):
    """Image document extractor - uses Vision model for processing"""
    
    def extract(self, file_path: str) -> Dict[str, Any]:
        """Extract image content"""
        try:
            import base64
            
            # Read image file
            with open(file_path, 'rb') as file:
                image_data = file.read()
            
            # Convert to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Get image information
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    width, height = img.size
                    format_name = img.format
                    mode = img.mode
            except Exception:
                width = height = 0
                format_name = Path(file_path).suffix.lstrip('.').upper()
                mode = 'unknown'
            
            # Create image description (can integrate Vision model here)
            image_description = f"Image file: {Path(file_path).name} ({width}x{height}, {format_name})"
            
            return {
                'content': f"[IMAGE_PLACEHOLDER]\n{image_description}",
                'metadata': {
                    'title': Path(file_path).stem,
                    'format': 'image',
                    'width': width,
                    'height': height,
                    'image_format': format_name,
                    'mode': mode,
                    'file_size': len(image_data)
                },
                'structure': {
                    'type': 'image',
                    'image_data': {
                        'base64': image_base64,
                        'format': format_name,
                        'size': (width, height)
                    }
                }
            }
        except Exception as e:
            logger.exception(f"Image content extraction failed: {e}")
            raise


class MarkdownExtractor(DocumentExtractor):
    """Markdown document extractor"""
    
    def extract(self, file_path: str) -> Dict[str, Any]:
        """Extract Markdown content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            # Parse title hierarchy
            headers = []
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if line.strip().startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    title = line.lstrip('#').strip()
                    headers.append({
                        'level': level,
                        'title': title,
                        'line': i + 1,
                        'position': sum(len(l) + 1 for l in lines[:i])
                    })
                
            return {
                'content': content,
                'metadata': {
                    'total_lines': len(lines),
                    'title': headers[0]['title'] if headers else Path(file_path).stem
                },
                'structure': {
                    'headers': headers,
                    'type': 'markdown'
                }
            }
        except Exception as e:
            logger.exception(f"Markdown content extraction failed: {e}")
            raise


class TextExtractor(DocumentExtractor):
    """Plain text extractor"""
    
    def extract(self, file_path: str) -> Dict[str, Any]:
        """Extract plain text content"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            return {
                'content': content,
                'metadata': {
                    'total_chars': len(content),
                    'title': Path(file_path).stem
                },
                'structure': {
                    'type': 'text'
                }
            }
        except Exception as e:
            logger.exception(f"Text content extraction failed: {e}")
            raise


class LLMDocumentChunker(BaseChunker):
    """
    LLM-based intelligent document chunker
    Uses large language models to understand document structure and perform semantic chunking
    """
    
    def __init__(self, config: Optional[ChunkingConfig] = None):
        super().__init__(config)
        self.max_retries = 3
        self.fallback_enabled = True
        
        # Document extractor mapping - supports more unstructured document types
        self.extractors = {
            # PDF documents
            '.pdf': EnhancedPDFExtractor(),
            # Markdown documents
            '.md': MarkdownExtractor(),
            '.markdown': MarkdownExtractor(),
            # Plain text
            '.txt': TextExtractor(),
            '.rst': ReStructuredTextExtractor(),
            # Word documents (can be added if needed)
            # '.docx': DocxExtractor(),
            # HTML documents
            '.html': HtmlExtractor(),
            '.htm': HtmlExtractor(),
            # Image files (processed using Vision model)
            '.png': ImageExtractor(),
            '.jpg': ImageExtractor(),
            '.jpeg': ImageExtractor(),
            '.gif': ImageExtractor(),
            '.bmp': ImageExtractor(),
            '.webp': ImageExtractor(),
        }
        
        # Supported document types
        self.supported_extensions = set(self.extractors.keys())
    
    def can_process(self, file_path: str) -> bool:
        """Check if this file type can be processed"""
        return Path(file_path).suffix.lower() in self.supported_extensions
    
    def chunk(self, context: RawContextProperties) -> Iterator[Chunk]:
        """
        Intelligently chunk documents
        
        Args:
            context: Raw context properties
            
        Yields:
            Chunk: Chunk objects
        """
        try:
            # Determine processing method based on context
            if context.content_text:
                # Process plain text content (like vaults documents)
                yield from self._chunk_text_content(context)
            elif context.content_path:
                # Process file content
                yield from self._chunk_file_content(context)
            else:
                logger.warning("No processable content found")
                return
                
        except Exception as e:
            logger.exception(f"LLM chunking failed: {e}")
            if self.fallback_enabled:
                logger.info("Enabling fallback mode, using traditional chunker")
                yield from self._fallback_chunking(context)
    
    def _chunk_text_content(self, context: RawContextProperties) -> Iterator[Chunk]:
        """Process plain text content (like vaults documents)"""
        content = context.content_text
        additional_info = context.additional_info or {}
        
        document_data = {
            'content': content,
            'metadata': {
                'title': additional_info.get('title', ''),
                'vault_id': additional_info.get('vault_id'),
                'document_type': additional_info.get('document_type', 'text')
            },
            'structure': {
                'type': 'vaults_document'
            }
        }
        
        # Call LLM for chunking
        chunks_data = self._llm_chunk_document(document_data, context)
        
        # Convert to Chunk objects
        for chunk_data in chunks_data:
            yield self._create_chunk_from_data(chunk_data, context)
    
    def _chunk_file_content(self, context: RawContextProperties) -> Iterator[Chunk]:
        """Process file content"""
        file_path = context.content_path
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in self.extractors:
            logger.warning(f"Unsupported file type: {file_ext}")
            return
        
        # Extract document content
        extractor = self.extractors[file_ext]
        document_data = extractor.extract(file_path)
        
        # Call LLM for chunking
        chunks_data = self._llm_chunk_document(document_data, context)
        
        # Convert to Chunk objects
        for chunk_data in chunks_data:
            yield self._create_chunk_from_data(chunk_data, context)
    
    def _llm_chunk_document(self, document_data: Dict[str, Any], context: RawContextProperties) -> List[Dict[str, Any]]:
        """Use LLM for document chunking"""
        
        for attempt in range(self.max_retries):
            try:
                # Build prompt
                system_prompt, user_prompt = self._build_chunking_prompt(document_data)
                
                # Call LLM
                response = generate_with_messages(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                
                # Parse response
                chunks_data = self._parse_llm_response(response)
                
                if chunks_data:
                    logger.info(f"LLM chunking successful, generated {len(chunks_data)} chunks")
                    return chunks_data
                
            except Exception as e:
                logger.warning(f"LLM chunking attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    continue
                raise
        
        raise RuntimeError("LLM chunking failed, max retries reached")
    
    def _build_chunking_prompt(self, document_data: Dict[str, Any]) -> Tuple[str, str]:
        """Build LLM chunking prompt"""
        content = document_data['content']
        metadata = document_data['metadata']
        structure = document_data['structure']
        
        system_prompt = """You are a professional document analysis expert, skilled in understanding document structure and performing intelligent chunking.

Your tasks:
1. Analyze document hierarchy (chapters, paragraphs, topics)
2. Identify semantic boundaries and logical units
3. Generate appropriately sized chunks while maintaining content integrity
4. Generate titles and summaries for each chunk
5. Identify relationships between chunks

Chunking principles:
- Maintain semantic integrity: don't split in the middle of sentences
- Topic consistency: keep same-topic content in the same chunk
- Preserve structure: retain original document hierarchy information
- Appropriate size: each chunk between 100-1000 characters

Return chunking results in JSON format:
{
  "chunks": [
    {
      "chunk_id": "chunk_1",
      "chunk_index": 0,
      "content": "chunk content",
      "title": "chunk title", 
      "summary": "chunk summary",
      "section_path": ["section path"],
      "metadata": {
        "start_position": 0,
        "end_position": 500,
        "semantic_type": "introduction",
        "importance": 8,
        "keywords": ["keyword1", "keyword2"]
      }
    }
  ]
}"""

        user_prompt = f"""Please analyze the following {structure.get('type', 'text')} document and perform intelligent chunking according to the specified principles:

Document title: {metadata.get('title', 'Untitled Document')}
Document type: {structure.get('type', 'text')}

Document content:
{content[:5000]}{'...(content truncated)' if len(content) > 5000 else ''}

Please return chunking results in JSON format."""

        return system_prompt, user_prompt
    
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response"""
        try:
            # Extract JSON content
            from opencontext.utils.json_parser import parse_json_from_response
            result = parse_json_from_response(response)
            
            chunks = result.get('chunks', [])
            if not chunks:
                raise ValueError("Response does not contain chunk data")
            
            # Validate chunk data format
            for i, chunk in enumerate(chunks):
                if not all(key in chunk for key in ['content', 'title']):
                    raise ValueError(f"Chunk {i} missing required fields")
            
            return chunks
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response}")
            raise
    
    def _create_chunk_from_data(self, chunk_data: Dict[str, Any], context: RawContextProperties) -> Chunk:
        """Create Chunk object from LLM returned data"""
        additional_info = context.additional_info or {}
        
        # Extract structured information
        chunk_metadata = chunk_data.get('metadata', {})
        section_path = chunk_data.get('section_path', [])
        
        # Create generic metadata (backward compatible)
        metadata = chunk_metadata.copy()
        metadata.update({
            'vault_id': additional_info.get('vault_id'),
            'document_title': additional_info.get('title', ''),
            'llm_generated': True,
            'raw_type': 'vaults' if additional_info.get('vault_id') else 'file'
        })
        
        # Detect image and table references in text
        content = chunk_data['content']
        referenced_images = []
        referenced_tables = []
        
        # Extract image references, e.g. [IMAGE:img_1_1]
        import re
        img_matches = re.findall(r'\[IMAGE:([^\]]+)\]', content)
        referenced_images.extend(img_matches)
        
        # Extract table references, e.g. [TABLE:table_1_1]
        table_matches = re.findall(r'\[TABLE:([^\]]+)\]', content)
        referenced_tables.extend(table_matches)
        
        return Chunk(
            text=content,
            chunk_index=chunk_data.get('chunk_index', 0),
            source_document_id=str(additional_info.get('vault_id', context.object_id)),
            title=chunk_data['title'],
            summary=chunk_data.get('summary', content[:200] + "..." if len(content) > 200 else content),
            
            # Position and reference information
            start_position=chunk_metadata.get('start_position'),
            end_position=chunk_metadata.get('end_position'),
            page_number=chunk_metadata.get('page_number'),
            section_path=section_path,
            
            # Associated image and table references
            referenced_images=referenced_images,
            referenced_tables=referenced_tables,
            
            # Semantic information
            semantic_type=chunk_metadata.get('semantic_type'),
            importance_score=chunk_metadata.get('importance', chunk_metadata.get('importance_score')),
            keywords=chunk_metadata.get('keywords', []),
            
            # Generic metadata (backward compatible)
            metadata=metadata
        )
    
    def _fallback_chunking(self, context: RawContextProperties) -> Iterator[Chunk]:
        """Fallback mode: use simple text splitting"""
        logger.info("Using simple text splitting for fallback chunking")
        
        # Get text content
        if context.content_text:
            content = context.content_text
        elif context.content_path:
            try:
                with open(context.content_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Failed to read file: {e}")
                return
        else:
            logger.warning("No available text content for fallback chunking")
            return
        
        # Simple length-based splitting
        chunk_size = 1000
        overlap = 200
        
        start = 0
        chunk_index = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk_text = content[start:end]
            
            if chunk_text.strip():
                yield Chunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    source_document_id=context.object_id,
                    title=f"Fallback Chunk {chunk_index + 1}",
                    summary=chunk_text[:100] + "..." if len(chunk_text) > 100 else chunk_text,
                    metadata={
                        'fallback_chunking': True,
                        'start_position': start,
                        'end_position': end
                    }
                )
                chunk_index += 1
            
            start = end - overlap
            if start >= len(content):
                break