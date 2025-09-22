#!/usr/bin/env python3
"""
Localization format handler for BG3 preview system
Handles: .loca localization files
"""

import os
from typing import Dict

from .base_handler import FormatHandler

class LocalizationHandler(FormatHandler):
    """Handler for localization files (.loca)"""
    
    def can_handle(self, file_ext: str) -> bool:
        """Check if this handler supports the file extension"""
        return file_ext.lower() == '.loca'
    
    def get_supported_extensions(self):
        """Return list of supported extensions"""
        return ['.loca']
    
    def get_file_icon(self, file_ext: str) -> str:
        """Get appropriate icon for file type"""
        return "🗄️"
    
    def preview(self, file_path: str, wine_wrapper=None, **kwargs) -> Dict:
        """Generate preview for .loca files"""
        preview_data = self._create_base_preview_data(file_path)
        
        if preview_data.get('error'):
            return preview_data
        
        try:
            # Generate header
            content = self._create_header_content(file_path)
            
            # Add localization analysis
            loca_analysis = self._analyze_loca_file(file_path, wine_wrapper)
            content += loca_analysis
            
            preview_data['content'] = content
            return preview_data
            
        except Exception as e:
            preview_data['error'] = str(e)
            preview_data['content'] = f"Error previewing .loca file: {e}"
            return preview_data
    
    def _analyze_loca_file(self, file_path: str, wine_wrapper=None) -> str:
        """Analyze .loca localization file"""
        try:
            content = "Localization File (.loca)\n\n"
            
            # Try using the LocaManager for parsing if available
            try:
                # This would need to be imported from your loca_manager module
                # Commenting out to avoid import errors in the isolated handler
                # from loca_manager import LocaManager
                # loca_manager = LocaManager(wine_wrapper, None)
                # parsed_data = loca_manager.parse_loca_file(file_path)
                
                # For now, fall back to binary analysis
                parsed_data = None
                
                if parsed_data and parsed_data.get('entries'):
                    content += self._format_parsed_loca_data(parsed_data)
                else:
                    content += "Could not parse .loca file with LocaManager.\n"
                    content += self._analyze_loca_binary_fallback(file_path)
                    
            except ImportError:
                # LocaManager not available, use fallback
                content += "LocaManager not available - using binary analysis.\n"
                content += self._analyze_loca_binary_fallback(file_path)
            
            return content
            
        except Exception as e:
            return f"Error analyzing .loca file: {e}\n"
    
    def _format_parsed_loca_data(self, parsed_data: Dict) -> str:
        """Format parsed localization data for display"""
        content = ""
        entries = parsed_data['entries']
        
        content += f"Successfully parsed!\n"
        content += f"Method: {parsed_data.get('format', 'unknown')}\n"
        content += f"Total entries: {len(entries)}\n\n"
        
        if entries:
            content += "Sample entries:\n"
            content += "-" * 50 + "\n"
            
            for i, entry in enumerate(entries[:5]):
                content += f"#{i+1}\n"
                content += f"Handle: {entry['handle']}\n"
                if entry['text']:
                    preview_text = entry['text'][:150]
                    if len(entry['text']) > 150:
                        preview_text += "..."
                    content += f"Text: {preview_text}\n"
                content += "\n"
            
            if len(entries) > 5:
                content += f"... and {len(entries) - 5} more entries\n"
                
            # Language detection
            if entries:
                content += self._detect_language_patterns(entries[:10])
        
        return content
    
    def _analyze_loca_binary_fallback(self, file_path: str) -> str:
        """Fallback binary analysis when divine.exe isn't available"""
        try:
            with open(file_path, 'rb') as f:
                data = f.read(512)  # Read first 512 bytes
            
            content = "\nBinary Analysis:\n"
            content += f"File size: {os.path.getsize(file_path):,} bytes\n"
            
            # Look for text patterns
            if b'content' in data.lower():
                content += "Contains 'content' - likely localization data\n"
            
            if b'handle' in data.lower():
                content += "Contains 'handle' - likely UUID references\n"
            
            if b'text' in data.lower():
                content += "Contains 'text' - likely string data\n"
            
            # Check for compression
            if data.startswith(b'\x1f\x8b'):
                content += "Format: GZIP compressed\n"
            elif data.startswith(b'PK'):
                content += "Format: ZIP compressed\n"
            elif data.startswith(b'LSOF'):
                content += "Format: Larian binary (LSOF)\n"
            else:
                content += "Format: Unknown binary\n"
            
            # Look for common localization patterns
            content += self._detect_binary_patterns(data)
            
            # Show readable strings
            readable_chars = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data[:100])
            content += f"Header preview: {readable_chars}\n"
            
            content += "\nNote: Install divine.exe for detailed .loca parsing.\n"
            
            return content
            
        except Exception as e:
            return f"\nBinary analysis failed: {e}\n"
    
    def _detect_binary_patterns(self, data: bytes) -> str:
        """Detect patterns in binary localization data"""
        patterns = ""
        
        # Count potential UUID patterns (hex strings)
        hex_like_count = data.count(b'-') + data.count(b'0x')
        if hex_like_count > 0:
            patterns += f"UUID-like patterns: {hex_like_count}\n"
        
        # Count null terminators (common in string tables)
        null_count = data.count(b'\x00')
        if null_count > 10:
            patterns += f"Null terminators: {null_count} (string table likely)\n"
        
        # Look for repeated byte patterns (compression indicators)
        if len(set(data)) < len(data) * 0.3:
            patterns += "High compression detected\n"
        
        # Look for XML-like patterns even in binary
        if b'<' in data and b'>' in data:
            patterns += "XML-like structures detected\n"
        
        return patterns
    
    def _detect_language_patterns(self, entries: list) -> str:
        """Detect language patterns in localization entries"""
        if not entries:
            return ""
        
        patterns = "\nLanguage Analysis:\n"
        
        # Collect sample text
        sample_texts = []
        for entry in entries[:10]:
            if entry.get('text'):
                sample_texts.append(entry['text'].lower())
        
        if not sample_texts:
            return patterns + "No text content found for analysis\n"
        
        combined_text = ' '.join(sample_texts)
        
        # Basic language detection patterns
        language_indicators = {
            'english': ['the ', 'and ', 'you ', 'are ', 'have ', 'will '],
            'french': ['le ', 'la ', 'les ', 'une ', 'des ', 'vous '],
            'german': ['der ', 'die ', 'das ', 'und ', 'ich ', 'sie '],
            'spanish': ['el ', 'la ', 'los ', 'las ', 'que ', 'con '],
            'italian': ['il ', 'la ', 'di ', 'che ', 'non ', 'con '],
            'russian': ['что ', 'это ', 'как ', 'так ', 'все ', 'был '],
            'japanese': ['は', 'が', 'を', 'に', 'で', 'と'],
            'chinese': ['的', '是', '了', '在', '我', '有']
        }
        
        detected_languages = []
        for lang, indicators in language_indicators.items():
            matches = sum(1 for indicator in indicators if indicator in combined_text)
            if matches >= 2:  # At least 2 indicators found
                detected_languages.append(f"{lang} ({matches} indicators)")
        
        if detected_languages:
            patterns += f"Possible languages: {', '.join(detected_languages)}\n"
        else:
            patterns += "Language: Unknown or mixed\n"
        
        # Text characteristics
        total_chars = len(combined_text)
        if total_chars > 0:
            alpha_ratio = sum(1 for c in combined_text if c.isalpha()) / total_chars
            patterns += f"Text density: {alpha_ratio:.1%} alphabetic characters\n"
        
        return patterns