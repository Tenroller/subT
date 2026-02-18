"""
Translator module using argos-translate for offline translation
"""
import asyncio
from typing import Optional
import argostranslate.package
import argostranslate.translate


class Translator:
    """Handles text translation using argos-translate library"""
    
    def __init__(self):
        self.installed_packages: set = set()
        self._initialized = False
    
    def _ensure_initialized(self):
        """Initialize package list on first use"""
        if not self._initialized:
            try:
                argostranslate.package.update_package_index()
            except Exception as e:
                print(f"Warning: Could not update package index: {e}")
            self._initialized = True
    
    def get_available_languages(self) -> list[dict]:
        """Get list of available target languages"""
        return [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "pt", "name": "Portuguese"},
            {"code": "it", "name": "Italian"},
            {"code": "zh", "name": "Chinese"},
            {"code": "ja", "name": "Japanese"},
            {"code": "ko", "name": "Korean"},
            {"code": "ru", "name": "Russian"},
            {"code": "ar", "name": "Arabic"},
        ]
    
    def ensure_package_installed(self, from_code: str, to_code: str) -> bool:
        """
        Install language package if not already installed.
        Returns True if package is available, False otherwise.
        """
        self._ensure_initialized()
        
        package_key = f"{from_code}->{to_code}"
        
        # Check if already installed
        if package_key in self.installed_packages:
            return True
        
        # Check installed packages
        installed = argostranslate.translate.get_installed_languages()
        from_lang = next((l for l in installed if l.code == from_code), None)
        
        if from_lang:
            to_lang = next((t for t in from_lang.get_translation(installed) 
                          if t.code == to_code), None)
            if to_lang:
                self.installed_packages.add(package_key)
                return True
        
        # Try to install the package
        try:
            available_packages = argostranslate.package.get_available_packages()
            package = next(
                (p for p in available_packages 
                 if p.from_code == from_code and p.to_code == to_code),
                None
            )
            
            if package:
                print(f"Installing translation package: {from_code} -> {to_code}")
                argostranslate.package.install_from_path(package.download())
                self.installed_packages.add(package_key)
                return True
            else:
                print(f"No package available for {from_code} -> {to_code}")
                return False
                
        except Exception as e:
            print(f"Error installing package {from_code} -> {to_code}: {e}")
            return False
    
    def translate_text(self, text: str, from_code: str, to_code: str) -> str:
        """
        Translate text from source language to target language.
        Returns original text if translation fails.
        """
        if not text or not text.strip():
            return text
            
        if from_code == to_code:
            return text
        
        try:
            if not self.ensure_package_installed(from_code, to_code):
                print(f"Package not available, returning original text")
                return text
            
            translated = argostranslate.translate.translate(text, from_code, to_code)
            return translated
            
        except Exception as e:
            print(f"Translation error: {e}")
            return text
    
    def translate_segments(
        self, 
        segments: list[dict], 
        from_code: str, 
        to_code: str
    ) -> list[dict]:
        """
        Translate all segments in transcription.
        Each segment should have 'text' and optionally 'words' keys.
        """
        if from_code == to_code:
            return segments
        
        # Ensure package is installed before processing
        if not self.ensure_package_installed(from_code, to_code):
            print(f"Cannot translate: package {from_code}->{to_code} not available")
            return segments
        
        translated_segments = []
        
        for segment in segments:
            new_segment = segment.copy()
            
            # Translate the main segment text
            if 'text' in segment:
                new_segment['text'] = self.translate_text(
                    segment['text'], from_code, to_code
                )
            
            # Translate individual words if present
            if 'words' in segment and segment['words']:
                new_words = []
                for word in segment['words']:
                    new_word = word.copy()
                    if 'word' in word:
                        new_word['word'] = self.translate_text(
                            word['word'], from_code, to_code
                        )
                    new_words.append(new_word)
                new_segment['words'] = new_words
            
            translated_segments.append(new_segment)
        
        return translated_segments


# Singleton instance
_translator: Optional[Translator] = None


def get_translator() -> Translator:
    """Get or create the translator singleton"""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator
