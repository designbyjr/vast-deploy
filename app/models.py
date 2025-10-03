"""
Pydantic models for API request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime
from fastapi import UploadFile


class TranscriptionRequest(BaseModel):
    """Request model for audio transcription via JSON with base64 data."""
    
    audio_data: str = Field(
        ...,
        description="Base64 encoded audio data",
        example="UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+D0t2kbCy+T2e/BeCkGK2+94NCVRgtc4e8="
    )


class TranscriptionFormRequest(BaseModel):
    """Request model for form-based audio file transcription."""
    
    model: str = Field(
        default="whisper-v3-turbo",
        description="Whisper model to use (tiny, base, small, medium, large, large-v2, large-v3, whisper-v3-turbo)",
        example="whisper-v3-turbo"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="Language code (auto-detect if not specified). Use ISO 639-1 codes like 'en', 'es', 'fr'",
        example="en"
    )
    
    task: str = Field(
        default="transcribe",
        description="Task type: 'transcribe' (speech to text) or 'translate' (speech to English)",
        example="transcribe"
    )
    
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (0.0 to 1.0). Higher values make output more random",
        example=0.0
    )
    
    word_timestamps: bool = Field(
        default=False,
        description="Include word-level timestamps in the output",
        example=False
    )
    
    initial_prompt: Optional[str] = Field(
        default=None,
        description="Optional text to provide as context or style guide for the model",
        example="The following is a meeting recording with technical discussion."
    )
    
    audio_format: Optional[str] = Field(
        default="wav",
        description="Audio format (wav, mp3, m4a, flac, ogg)",
        example="wav"
    )
    
    model: Optional[str] = Field(
        default="whisper-v3-turbo",
        description="Whisper model to use (tiny, base, small, medium, large, large-v2, large-v3, whisper-v3-turbo)",
        example="whisper-v3-turbo"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="Language code (auto-detect if not specified)",
        example="en"
    )
    
    task: Optional[str] = Field(
        default="transcribe",
        description="Task type (transcribe or translate)",
        example="transcribe"
    )
    
    temperature: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sampling temperature (0.0 to 1.0)",
        example=0.0
    )
    
    word_timestamps: Optional[bool] = Field(
        default=False,
        description="Include word-level timestamps",
        example=False
    )
    
    initial_prompt: Optional[str] = Field(
        default=None,
        description="Initial prompt to guide the model",
        example="Hello, this is a test recording."
    )


class TranscriptionResponse(BaseModel):
    """Response model for audio transcription."""
    
    transcription: str = Field(
        ...,
        description="The transcribed text",
        example="Hello, this is a test recording of the Whisper ASR system."
    )
    
    language: str = Field(
        ...,
        description="Detected or specified language",
        example="en"
    )
    
    model: str = Field(
        ...,
        description="Model used for transcription",
        example="base"
    )
    
    duration: Optional[float] = Field(
        default=None,
        description="Audio duration in seconds",
        example=5.2
    )
    
    processing_time: Optional[float] = Field(
        default=None,
        description="Processing time in seconds", 
        example=1.8
    )
    
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0)",
        example=0.95
    )
    
    segments: Optional[List[dict]] = Field(
        default=None,
        description="Transcription segments with timestamps",
        example=[
            {
                "id": 0,
                "start": 0.0,
                "end": 5.2,
                "text": "Hello, this is a test recording.",
                "tokens": [50364, 2425, 11, 341, 307, 257, 1500, 6613, 13, 50614],
                "temperature": 0.0,
                "avg_logprob": -0.18,
                "compression_ratio": 1.2,
                "no_speech_prob": 0.01
            }
        ]
    )
    
    words: Optional[List[dict]] = Field(
        default=None,
        description="Word-level timestamps (if requested)",
        example=[
            {"word": "Hello", "start": 0.1, "end": 0.5, "probability": 0.99},
            {"word": "this", "start": 0.6, "end": 0.8, "probability": 0.98}
        ]
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Response timestamp",
        example="2025-10-03T17:30:00.000Z"
    )


class ModelsResponse(BaseModel):
    """Response model for available models."""
    
    current_engine: str = Field(
        ...,
        description="Current ASR engine",
        example="faster_whisper"
    )
    
    current_model: str = Field(
        ...,
        description="Currently loaded model",
        example="base"
    )
    
    available_models: List[str] = Field(
        ...,
        description="List of available models",
        example=["tiny", "base", "small", "medium", "large"]
    )
    
    model_info: Optional[dict] = Field(
        default=None,
        description="Detailed model information",
        example={
            "base": {
                "size": "74MB",
                "languages": ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"],
                "parameters": "39M",
                "relative_speed": "1.0x"
            }
        }
    )
    
    device: str = Field(
        ...,
        description="Processing device",
        example="cpu"
    )
    
    quantization: str = Field(
        ...,
        description="Model quantization",
        example="int8"
    )


class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(
        ...,
        description="Error message",
        example="Invalid audio format"
    )
    
    code: Optional[str] = Field(
        default=None,
        description="Error code",
        example="INVALID_AUDIO_FORMAT"
    )
    
    details: Optional[dict] = Field(
        default=None,
        description="Additional error details"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Error timestamp"
    )


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(
        ...,
        description="Health status",
        example="healthy"
    )
    
    healthy: bool = Field(
        ...,
        description="Boolean health indicator",
        example=True
    )
    
    timestamp: datetime = Field(
        ...,
        description="Health check timestamp"
    )


class DetailedHealthResponse(BaseModel):
    """Detailed health response model."""
    
    status: str = Field(..., example="healthy")
    healthy: bool = Field(..., example=True)
    timestamp: datetime = Field(...)
    
    components: Optional[dict] = Field(
        default=None,
        description="Component health status",
        example={
            "redis": {"status": "connected", "response_time": "2ms"},
            "whisper": {"status": "loaded", "model": "base"},
            "tls": {"status": "enabled", "cert_expiry": "2026-10-03"}
        }
    )
    
    metrics: Optional[dict] = Field(
        default=None,
        description="System metrics",
        example={
            "uptime": "1h 30m",
            "requests_processed": 1234,
            "avg_response_time": "150ms",
            "memory_usage": "245MB"
        }
    )