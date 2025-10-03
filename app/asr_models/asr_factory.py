"""
ASR Engine Factory for Whisper implementations.
Supports OpenAI Whisper, Faster Whisper, and WhisperX.
"""

import logging
import os
from typing import Optional, Dict, Any, Union
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ASREngine(ABC):
    """Abstract base class for ASR engines."""
    
    def __init__(self, model_name: str, device: str = "cpu", **kwargs):
        self.model_name = model_name
        self.device = device
        self.model = None
        self.is_loaded = False
        
    @abstractmethod
    async def load_model(self):
        """Load the ASR model."""
        pass
    
    @abstractmethod
    async def unload_model(self):
        """Unload the ASR model."""
        pass
    
    @abstractmethod
    async def transcribe(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """Transcribe audio file."""
        pass


class OpenAIWhisperEngine(ASREngine):
    """OpenAI Whisper implementation."""
    
    async def load_model(self):
        """Load OpenAI Whisper model."""
        try:
            import whisper
            logger.info(f"Loading OpenAI Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name, device=self.device)
            self.is_loaded = True
            logger.info(f"OpenAI Whisper model {self.model_name} loaded successfully")
        except ImportError:
            raise ImportError("OpenAI Whisper not installed. Install with: pip install openai-whisper")
        except Exception as e:
            logger.error(f"Failed to load OpenAI Whisper model: {e}")
            raise
    
    async def unload_model(self):
        """Unload OpenAI Whisper model."""
        if self.model:
            del self.model
            self.model = None
            self.is_loaded = False
            logger.info(f"OpenAI Whisper model {self.model_name} unloaded")
    
    async def transcribe(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """Transcribe using OpenAI Whisper."""
        if not self.is_loaded:
            await self.load_model()
        
        try:
            # Extract parameters
            language = kwargs.get('language', None)
            task = kwargs.get('task', 'transcribe')
            initial_prompt = kwargs.get('initial_prompt', None)
            temperature = kwargs.get('temperature', 0.0)
            word_timestamps = kwargs.get('word_timestamps', False)
            
            # Transcribe
            result = self.model.transcribe(
                audio_path,
                language=language,
                task=task,
                initial_prompt=initial_prompt,
                temperature=temperature,
                word_timestamps=word_timestamps
            )
            
            # Format response
            segments = []
            words = []
            
            if 'segments' in result:
                for seg in result['segments']:
                    segments.append({
                        'id': seg.get('id', 0),
                        'start': seg.get('start', 0.0),
                        'end': seg.get('end', 0.0),
                        'text': seg.get('text', ''),
                        'temperature': temperature,
                        'avg_logprob': seg.get('avg_logprob', 0.0),
                        'compression_ratio': seg.get('compression_ratio', 0.0),
                        'no_speech_prob': seg.get('no_speech_prob', 0.0)
                    })
                    
                    if word_timestamps and 'words' in seg:
                        for word in seg['words']:
                            words.append({
                                'word': word.get('word', ''),
                                'start': word.get('start', 0.0),
                                'end': word.get('end', 0.0),
                                'probability': word.get('probability', 1.0)
                            })
            
            return {
                'text': result.get('text', ''),
                'language': result.get('language', language or 'unknown'),
                'segments': segments if word_timestamps else None,
                'words': words if word_timestamps else None
            }
            
        except Exception as e:
            logger.error(f"OpenAI Whisper transcription error: {e}")
            raise


class FasterWhisperEngine(ASREngine):
    """Faster Whisper implementation."""
    
    async def load_model(self):
        """Load Faster Whisper model."""
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Faster Whisper model: {self.model_name}")
            
            # Determine compute type based on device
            compute_type = "int8" if self.device == "cpu" else "float16"
            
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=compute_type
            )
            self.is_loaded = True
            logger.info(f"Faster Whisper model {self.model_name} loaded successfully")
        except ImportError:
            raise ImportError("Faster Whisper not installed. Install with: pip install faster-whisper")
        except Exception as e:
            logger.error(f"Failed to load Faster Whisper model: {e}")
            raise
    
    async def unload_model(self):
        """Unload Faster Whisper model."""
        if self.model:
            del self.model
            self.model = None
            self.is_loaded = False
            logger.info(f"Faster Whisper model {self.model_name} unloaded")
    
    async def transcribe(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """Transcribe using Faster Whisper."""
        if not self.is_loaded:
            await self.load_model()
        
        try:
            # Extract parameters
            language = kwargs.get('language', None)
            task = kwargs.get('task', 'transcribe')
            initial_prompt = kwargs.get('initial_prompt', None)
            temperature = kwargs.get('temperature', 0.0)
            word_timestamps = kwargs.get('word_timestamps', False)
            
            # Transcribe
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                task=task,
                initial_prompt=initial_prompt,
                temperature=temperature,
                word_timestamps=word_timestamps
            )
            
            # Format response
            transcription = ""
            formatted_segments = []
            words = []
            
            for segment in segments:
                transcription += segment.text
                
                formatted_segments.append({
                    'id': segment.id,
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text,
                    'temperature': temperature,
                    'avg_logprob': segment.avg_logprob,
                    'compression_ratio': segment.compression_ratio,
                    'no_speech_prob': segment.no_speech_prob
                })
                
                if word_timestamps and hasattr(segment, 'words'):
                    for word in segment.words:
                        words.append({
                            'word': word.word,
                            'start': word.start,
                            'end': word.end,
                            'probability': word.probability
                        })
            
            return {
                'text': transcription,
                'language': info.language,
                'segments': formatted_segments if word_timestamps else None,
                'words': words if word_timestamps else None,
                'duration': info.duration
            }
            
        except Exception as e:
            logger.error(f"Faster Whisper transcription error: {e}")
            raise


class ASREngineFactory:
    """Factory for creating ASR engines."""
    
    _engines = {
        'openai_whisper': OpenAIWhisperEngine,
        'faster_whisper': FasterWhisperEngine,
    }
    
    @classmethod
    def create_engine(cls, engine_type: str, model_name: str, device: str = "cpu", **kwargs) -> ASREngine:
        """Create an ASR engine instance."""
        if engine_type not in cls._engines:
            raise ValueError(f"Unsupported engine type: {engine_type}. Available: {list(cls._engines.keys())}")
        
        engine_class = cls._engines[engine_type]
        return engine_class(model_name, device, **kwargs)
    
    @classmethod
    def list_engines(cls) -> list:
        """List available engine types."""
        return list(cls._engines.keys())


# Global engine instance
_current_engine: Optional[ASREngine] = None


async def get_asr_engine(engine_type: str, model_name: str, device: str = "cpu") -> ASREngine:
    """Get or create ASR engine instance."""
    global _current_engine
    
    # Check if we need to load a different engine/model
    if (_current_engine is None or 
        type(_current_engine).__name__.lower() != engine_type.lower() + 'engine' or
        _current_engine.model_name != model_name or
        _current_engine.device != device):
        
        # Unload current engine
        if _current_engine:
            await _current_engine.unload_model()
        
        # Create new engine
        _current_engine = ASREngineFactory.create_engine(engine_type, model_name, device)
        await _current_engine.load_model()
    
    return _current_engine


async def cleanup_asr_engine():
    """Cleanup ASR engine resources."""
    global _current_engine
    if _current_engine:
        await _current_engine.unload_model()
        _current_engine = None