"""
Audio processing utilities for Whisper ASR service.
Handles file format conversion, preprocessing, and temporary file management.
"""

import os
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import aiofiles

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Audio processing utilities."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.gettempdir()
        
    async def save_uploaded_file(self, audio_file, filename: Optional[str] = None) -> str:
        """Save uploaded file to temporary location."""
        try:
            # Create temporary file
            suffix = ""
            if filename:
                suffix = Path(filename).suffix.lower()
            elif hasattr(audio_file, 'filename') and audio_file.filename:
                suffix = Path(audio_file.filename).suffix.lower()
            
            # Create temp file
            temp_fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=self.temp_dir)
            
            # Close the file descriptor first
            os.close(temp_fd)
            
            # Write file content using the path
            if hasattr(audio_file, 'read'):
                # UploadFile object
                content = await audio_file.read()
                with open(temp_path, 'wb') as f:
                    f.write(content)
            else:
                # Direct bytes
                with open(temp_path, 'wb') as f:
                    f.write(audio_file)
            logger.debug(f"Saved uploaded file to: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            raise
    
    async def convert_to_wav(self, input_path: str, output_path: Optional[str] = None) -> str:
        """Convert audio file to WAV format using FFmpeg."""
        try:
            if not output_path:
                output_fd, output_path = tempfile.mkstemp(suffix='.wav', dir=self.temp_dir)
                os.close(output_fd)
            
            # FFmpeg command for conversion
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-ar', '16000',          # 16kHz sample rate
                '-ac', '1',              # Mono
                '-y',                    # Overwrite output
                output_path
            ]
            
            # Run FFmpeg
            process = await self._run_command(cmd)
            if process.returncode != 0:
                raise RuntimeError(f"FFmpeg conversion failed: {process.stderr}")
            
            logger.debug(f"Converted audio to WAV: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            raise
    
    async def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """Get audio file information using FFprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                audio_path
            ]
            
            process = await self._run_command(cmd)
            if process.returncode != 0:
                raise RuntimeError(f"FFprobe failed: {process.stderr}")
            
            import json
            info = json.loads(process.stdout)
            
            # Extract audio stream info
            audio_stream = None
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break
            
            if not audio_stream:
                raise ValueError("No audio stream found in file")
            
            format_info = info.get('format', {})
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'format_name': format_info.get('format_name', 'unknown'),
                'size': int(format_info.get('size', 0)),
                'bit_rate': int(format_info.get('bit_rate', 0)),
                'codec_name': audio_stream.get('codec_name', 'unknown'),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'bits_per_sample': audio_stream.get('bits_per_sample', 16)
            }
            
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            # Return minimal info if FFprobe fails
            return {
                'duration': 0.0,
                'format_name': 'unknown',
                'size': os.path.getsize(audio_path) if os.path.exists(audio_path) else 0,
                'bit_rate': 0,
                'codec_name': 'unknown',
                'sample_rate': 16000,
                'channels': 1,
                'bits_per_sample': 16
            }
    
    async def validate_audio_file(self, audio_path: str) -> bool:
        """Validate that the file is a valid audio file."""
        try:
            info = await self.get_audio_info(audio_path)
            
            # Check if we got valid audio info
            if (info['duration'] > 0 and 
                info['sample_rate'] > 0 and 
                info['channels'] > 0):
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Audio validation failed: {e}")
            return False
    
    async def preprocess_audio(self, input_path: str, encode: bool = True) -> str:
        """Preprocess audio for Whisper transcription."""
        try:
            # Validate input file
            if not await self.validate_audio_file(input_path):
                raise ValueError("Invalid audio file")
            
            # If encoding is disabled, return original path
            if not encode:
                logger.debug("Audio encoding disabled, using original file")
                return input_path
            
            # Get audio info
            info = await self.get_audio_info(input_path)
            logger.debug(f"Audio info: {info}")
            
            # Check if conversion is needed
            needs_conversion = (
                info['codec_name'] not in ['pcm_s16le', 'wav'] or
                info['sample_rate'] != 16000 or
                info['channels'] != 1
            )
            
            if needs_conversion:
                logger.info("Converting audio to optimal format for Whisper")
                return await self.convert_to_wav(input_path)
            else:
                logger.debug("Audio already in optimal format")
                return input_path
            
        except Exception as e:
            logger.error(f"Audio preprocessing failed: {e}")
            raise
    
    async def cleanup_temp_file(self, file_path: str):
        """Clean up temporary file."""
        try:
            if os.path.exists(file_path) and self.temp_dir in file_path:
                os.unlink(file_path)
                logger.debug(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
    
    async def _run_command(self, cmd: list) -> subprocess.CompletedProcess:
        """Run shell command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            return type('CompletedProcess', (), {
                'returncode': process.returncode,
                'stdout': stdout.decode('utf-8'),
                'stderr': stderr.decode('utf-8')
            })()
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            raise


# Global audio processor instance
audio_processor = AudioProcessor()


import asyncio