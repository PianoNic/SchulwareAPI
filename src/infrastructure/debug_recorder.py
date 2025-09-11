import asyncio
import os
import tempfile
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
from playwright.async_api import Page, BrowserContext
from src.infrastructure.logging_config import get_logger

logger = get_logger("debug_recorder")

class AuthenticationDebugRecorder:
    """
    Handles video recording during authentication and Discord error reporting.
    """
    
    def __init__(self):
        self.video_path: Optional[str] = None
        self.recording_enabled = os.getenv("DEBUG_VIDEO_RECORDING", "false").lower() == "true"
        self.discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.temp_dir = None
        
    async def start_recording(self, context: BrowserContext) -> Optional[str]:
        """
        Start video recording for the browser context.
        
        Args:
            context: Playwright browser context
            
        Returns:
            Path to the video file if recording started, None otherwise
        """
        if not self.recording_enabled:
            return None
            
        try:
            # Ensure debug_video directory exists
            debug_video_dir = Path("debug_video")
            debug_video_dir.mkdir(exist_ok=True)
            
            # Create subdirectory with timestamp for this session
            timestamp = int(time.time())
            session_dir = debug_video_dir / f"session_{timestamp}"
            session_dir.mkdir(exist_ok=True)
            self.temp_dir = str(session_dir)
            
            # Generate unique video filename
            video_hash = hashlib.md5(f"{timestamp}".encode()).hexdigest()
            video_filename = f"{video_hash}.webm"
            self.video_path = os.path.join(self.temp_dir, video_filename)
            
            # Start recording on the context
            await context.start_tracing(
                screenshots=True,
                snapshots=True,
                sources=True
            )
            
            logger.info("Video recording enabled - recording entire authentication session")
            logger.info(f"Starting video recording of complete authentication session")
            return self.video_path
            
        except Exception as e:
            logger.warning(f"Failed to start video recording: {e}")
            return None
    
    async def stop_recording(self, context: BrowserContext) -> Optional[str]:
        """
        Stop video recording and save the file.
        
        Args:
            context: Playwright browser context
            
        Returns:
            Path to the saved video file if successful, None otherwise
        """
        if not self.recording_enabled or not self.video_path:
            return None
            
        try:
            # Stop the trace and save it
            trace_path = self.video_path.replace('.webm', '.zip')
            await context.stop_tracing(path=trace_path)
            
            logger.info(f"Video recording completed: {self.video_path}")
            return self.video_path
            
        except Exception as e:
            logger.warning(f"Failed to stop video recording: {e}")
            return None
    
    async def send_error_report_to_discord(self, error_details: Dict[str, Any]) -> bool:
        """
        Send error report with video to Discord webhook.
        
        Args:
            error_details: Dictionary containing error information
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.discord_webhook_url:
            logger.warning("Discord webhook URL not configured, skipping error report")
            return False
            
        try:
            # Prepare the error message
            error_msg = self._format_error_message(error_details)
            
            # Send the message (with video if available)
            success = await self._send_discord_message(error_msg)
            
            if success:
                logger.info("Error report sent to Discord successfully")
            else:
                logger.warning("Failed to send error report to Discord")
                
            return success
            
        except Exception as e:
            logger.error(f"Error sending Discord report: {e}")
            return False
    
    def _format_error_message(self, error_details: Dict[str, Any]) -> str:
        """Format error details into a Discord message."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        
        message = f"🚨 **Authentication Error Report** 🚨\n\n"
        message += f"**Time:** {timestamp}\n"
        message += f"**Error:** {error_details.get('error', 'Unknown error')}\n"
        
        if 'email' in error_details:
            # Obfuscate email for privacy
            email = error_details['email']
            if '@' in email:
                username, domain = email.split('@', 1)
                obfuscated = f"{username[:2]}***@{domain}"
                message += f"**User:** {obfuscated}\n"
        
        if 'step' in error_details:
            message += f"**Failed Step:** {error_details['step']}\n"
            
        if 'duration' in error_details:
            message += f"**Duration:** {error_details['duration']:.2f}s\n"
            
        if 'additional_info' in error_details:
            message += f"**Additional Info:** {error_details['additional_info']}\n"
            
        message += f"\n**Video Recording:** {'Attached' if self.video_path and os.path.exists(self.video_path) else 'Not available'}"
        
        return message
    
    async def _send_discord_message(self, message: str) -> bool:
        """Send message to Discord webhook."""
        try:
            payload = {
                "content": message,
                "username": "SchulwareAPI Debug Bot",
                "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if self.video_path and os.path.exists(self.video_path):
                    # Send with video attachment
                    with open(self.video_path, 'rb') as video_file:
                        files = {"file": ("auth_debug.zip", video_file, "application/zip")}
                        data = {"payload_json": httpx._content.encode_json(payload)}
                        
                        response = await client.post(
                            self.discord_webhook_url,
                            data=data,
                            files=files
                        )
                else:
                    # Send text only
                    response = await client.post(
                        self.discord_webhook_url,
                        json=payload
                    )
                
                if response.status_code in [200, 204]:
                    return True
                else:
                    logger.warning(f"Discord webhook returned status {response.status_code}: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False
    
    def cleanup(self):
        """Clean up temporary files and directories (optional - videos persist for debugging)."""
        try:
            # Note: We don't automatically delete debug videos anymore
            # They persist in debug_video/ folder for manual inspection
            logger.debug("Debug recorder cleanup completed (videos preserved in debug_video/)")
            
        except Exception as e:
            logger.warning(f"Error during debug recorder cleanup: {e}")
    
    def __del__(self):
        """Ensure cleanup on object destruction."""
        self.cleanup()


# Global recorder instance for convenience
_recorder = None

def get_debug_recorder() -> AuthenticationDebugRecorder:
    """Get the global debug recorder instance."""
    global _recorder
    if _recorder is None:
        _recorder = AuthenticationDebugRecorder()
    return _recorder