#!/usr/bin/env python3
"""
Streaming Vision Pipeline with Conversation History - FIXED VERSION v3
Real-time desktop monitoring with VLM + character personalities + memory

Fixed Issues (v3):
- ✅ Smarter monitoring with activity detection
- ✅ Focus mode - monitor only active window
- ✅ Scheduled monitoring - auto-start/stop
- ✅ Trigger words - selective notifications
- ✅ Image change detection (skip if screen unchanged)

Previous (v2):
- ✅ Message deduplication - prevents repetitive spam
- ✅ Screen cropping - excludes chat interface from capture (left 75%)
- ✅ Conversation history (remembers context)
- ✅ Strong repetition penalties
- ✅ Dynamic character loading from ./chars/
- ✅ Vision history modes (clear/temporal/keep)
"""

import asyncio
import time
import base64
import io
import re
from datetime import datetime, time as dt_time
from difflib import SequenceMatcher
from PIL import Image, ImageGrab, ImageChops
import mss
from openai import AsyncOpenAI
from typing import Optional, List, Dict, Tuple

try:
    from character_profiles_dynamic import get_character_profiles, get_character_dict
except ImportError:
    print("⚠️  Warning: character_profiles_dynamic.py not found!")
    print("   Using basic fallback character system")
    def get_character_profiles():
        return {"default": "You are a helpful AI assistant."}
    def get_character_dict(name):
        return {"name": "Assistant", "role": "AI Helper"}


class StreamingVisionPipeline:
    """
    Real-time desktop vision assistant with character personalities and conversation history.
    """
    
    def __init__(
        self,
        vllm_url: str = "http://localhost:8000/v1",
        model_name: str = "Qwen3-VL-Thinking",
        character: str = "maya",
        user_context: Optional[str] = None,
        fps: float = 2.0,
        context_frames: int = 1,
        monitor_id: int = 1,
        crop_right_percent: float = 25.0,
        similarity_threshold: float = 0.80,
        # NEW: Smarter Monitoring v3
        activity_detection: bool = True,
        activity_threshold: float = 5.0,  # % of pixels changed
        focus_mode: bool = False,  # Only monitor active window
        trigger_words: Optional[List[str]] = None,  # Keywords to watch for
        schedule_start: Optional[str] = None,  # Format: "HH:MM" (24h)
        schedule_end: Optional[str] = None  # Format: "HH:MM" (24h)
    ):
        """
        Initialize the streaming vision pipeline.

        Args:
            vllm_url: vLLM server endpoint
            model_name: Model to use for inference
            character: Character key to use (loads from ./chars/{character}.yaml)
            user_context: Optional context about the user
            fps: Frames per second for continuous monitoring
            context_frames: Number of recent frames to include
            monitor_id: Which monitor to capture (1=primary)
            crop_right_percent: Percentage of right side to crop (0-100)
            similarity_threshold: Skip message if similarity > this (0.0-1.0)
            activity_detection: Only analyze when screen changes significantly
            activity_threshold: % of pixels that must change (0-100)
            focus_mode: Only capture active window instead of full screen
            trigger_words: List of keywords to watch for (case-insensitive)
            schedule_start: Start monitoring at this time (24h format)
            schedule_end: Stop monitoring at this time (24h format)
        """
        self.client = AsyncOpenAI(base_url=vllm_url, api_key="dummy")
        self.model_name = model_name
        self.fps = fps
        self.context_frames = context_frames
        self.user_context = user_context
        self.monitor_id = monitor_id
        self.crop_right_percent = crop_right_percent
        self.similarity_threshold = similarity_threshold

        # NEW: Smarter monitoring settings
        self.activity_detection = activity_detection
        self.activity_threshold = activity_threshold
        self.focus_mode = focus_mode
        self.trigger_words = [w.lower() for w in trigger_words] if trigger_words else []
        self.schedule_start = self._parse_time(schedule_start) if schedule_start else None
        self.schedule_end = self._parse_time(schedule_end) if schedule_end else None

        # Frame buffer
        self.frame_buffer = []
        self.last_frame_image = None  # For activity detection

        # Character loading
        self.load_character(character)

        # State
        self.running = False
        self.last_response = None
        self.last_monitoring_message = None  # Track last message for deduplication

        # Vision history mode - how to handle image context
        self.vision_history_mode = "clear"  # Options: "clear", "temporal", "keep"

        # Conversation history (text only, no images)
        self.conversation_history = []
        self.max_history = 100  # Keep last 10 exchanges (20 messages)

        # Statistics
        self.stats = {
            "frames_analyzed": 0,
            "frames_skipped_no_change": 0,
            "frames_skipped_duplicate": 0,
            "frames_skipped_schedule": 0
        }

        print(f"🎭 Loaded character: {self.character_dict['name']} ({self.character_dict['role']})")
        if user_context:
            print(f"👤 User context loaded ({len(user_context)} chars)")

        # Get monitor info for display (thread-safe way)
        with mss.mss() as sct:
            monitor = sct.monitors[monitor_id]
            print(f"📺 Monitoring: {monitor['width']}x{monitor['height']} @ {fps} FPS")
        print(f"🖼️  Context frames: {context_frames}")
        print(f"👁️  Vision mode: {self.vision_history_mode}")
        print(f"✂️  Screen crop: {100-crop_right_percent:.0f}% (excluding right {crop_right_percent:.0f}%)")
        print(f"🔄 Similarity threshold: {similarity_threshold*100:.0f}%")

        # NEW: Display smarter monitoring settings
        if self.activity_detection:
            print(f"⚡ Activity detection: ON (threshold: {activity_threshold}%)")
        if self.focus_mode:
            print(f"🎯 Focus mode: ON (active window only)")
        if self.trigger_words:
            print(f"🔔 Trigger words: {', '.join(self.trigger_words)}")
        if self.schedule_start or self.schedule_end:
            start_str = self.schedule_start.strftime("%H:%M") if self.schedule_start else "none"
            end_str = self.schedule_end.strftime("%H:%M") if self.schedule_end else "none"
            print(f"⏰ Schedule: {start_str} - {end_str}")

    def _parse_time(self, time_str: str) -> Optional[dt_time]:
        """Parse time string in HH:MM format to datetime.time object."""
        try:
            hour, minute = map(int, time_str.split(':'))
            return dt_time(hour, minute)
        except:
            print(f"⚠️  Invalid time format: {time_str} (expected HH:MM)")
            return None

    def is_within_schedule(self) -> bool:
        """Check if current time is within monitoring schedule."""
        if not self.schedule_start and not self.schedule_end:
            return True  # No schedule set, always monitor

        now = datetime.now().time()

        # Handle case where schedule crosses midnight
        if self.schedule_start and self.schedule_end:
            if self.schedule_start <= self.schedule_end:
                # Normal case: 09:00 - 17:00
                return self.schedule_start <= now <= self.schedule_end
            else:
                # Crosses midnight: 22:00 - 06:00
                return now >= self.schedule_start or now <= self.schedule_end
        elif self.schedule_start:
            # Only start time, monitor from start until midnight
            return now >= self.schedule_start
        elif self.schedule_end:
            # Only end time, monitor from midnight until end
            return now <= self.schedule_end

        return True

    def detect_screen_activity(self, current_image: Image.Image) -> Tuple[bool, float]:
        """
        Detect if screen has changed significantly.

        Args:
            current_image: Current screen capture

        Returns:
            Tuple of (has_changed, change_percentage)
        """
        if not self.activity_detection:
            return True, 100.0  # Always consider active if detection disabled

        if self.last_frame_image is None:
            self.last_frame_image = current_image
            return True, 100.0  # First frame, always process

        try:
            # Calculate difference
            diff = ImageChops.difference(self.last_frame_image, current_image)

            # Convert to grayscale and get histogram
            diff_gray = diff.convert('L')
            histogram = diff_gray.histogram()

            # Count non-zero pixels (changed pixels)
            total_pixels = diff_gray.size[0] * diff_gray.size[1]
            changed_pixels = sum(histogram[1:])  # Exclude histogram[0] which is black (no change)

            change_percentage = (changed_pixels / total_pixels) * 100

            # Update last frame
            self.last_frame_image = current_image

            has_changed = change_percentage >= self.activity_threshold

            if not has_changed:
                print(f"⏭️  Skipping - no activity ({change_percentage:.2f}% < {self.activity_threshold}%)")

            return has_changed, change_percentage

        except Exception as e:
            print(f"⚠️  Activity detection error: {e}")
            return True, 100.0  # On error, assume changed

    def check_trigger_words(self, text: str) -> bool:
        """
        Check if text contains any trigger words.

        Args:
            text: Text to check

        Returns:
            True if trigger words found or no triggers set, False otherwise
        """
        if not self.trigger_words:
            return True  # No triggers set, always process

        text_lower = text.lower()
        for trigger in self.trigger_words:
            if trigger in text_lower:
                print(f"🔔 Trigger word detected: '{trigger}'")
                return True

        return False

    def get_stats_summary(self) -> str:
        """Get formatted statistics summary."""
        total = sum(self.stats.values())
        if total == 0:
            return "No frames processed yet"

        return (
            f"📊 Stats: {self.stats['frames_analyzed']} analyzed, "
            f"{self.stats['frames_skipped_no_change']} skipped (no change), "
            f"{self.stats['frames_skipped_duplicate']} skipped (duplicate), "
            f"{self.stats['frames_skipped_schedule']} skipped (schedule)"
        )

    def load_character(self, character_key: str):
        """Load a character profile by key."""
        profiles = get_character_profiles()
        if character_key not in profiles:
            raise ValueError(f"Unknown character: {character_key}. Available: {list(profiles.keys())}")

        self.system_prompt = profiles[character_key]
        self.character_dict = get_character_dict(character_key)
        
        # Add user context to system prompt if provided
        if self.user_context:
            user_section = f"""

---
ABOUT THE USER YOU'RE OBSERVING:

{self.user_context}

Keep this context in mind when providing feedback and commentary.
"""
            self.system_prompt += user_section

    def switch_character(self, character_key: str):
        """Switch to a different character mid-session."""
        self.load_character(character_key)
        print(f"🎭 Switched to: {self.character_dict['name']}")
    
    def clear_history(self, reset_stats: bool = False):
        """Clear conversation history and frame buffer."""
        self.conversation_history = []
        self.frame_buffer = []
        self.last_monitoring_message = None
        self.last_frame_image = None  # Reset activity detection
        if reset_stats:
            self.stats = {
                "frames_analyzed": 0,
                "frames_skipped_no_change": 0,
                "frames_skipped_duplicate": 0,
                "frames_skipped_schedule": 0
            }
            print("🗑️  Conversation history and stats cleared")
        else:
            print("🗑️  Conversation history cleared")
    
    def get_history_summary(self) -> str:
        """Get a summary of conversation history."""
        return f"History: {len(self.conversation_history)} messages, {len(self.frame_buffer)} frames"

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity ratio between two strings.
        
        Returns:
            Float between 0.0 (completely different) and 1.0 (identical)
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize: lowercase, strip whitespace
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, text1, text2).ratio()
    
    def is_duplicate_message(self, new_message: str) -> bool:
        """
        Check if new message is too similar to the last one.
        
        Args:
            new_message: The new message to check
            
        Returns:
            True if message should be skipped (duplicate), False otherwise
        """
        if not self.last_monitoring_message:
            return False
        
        similarity = self.calculate_similarity(new_message, self.last_monitoring_message)
        
        if similarity > self.similarity_threshold:
            print(f"🔕 Skipping duplicate message (similarity: {similarity*100:.1f}%)")
            return True
        
        return False

    def capture_frame(self) -> Tuple[str, Image.Image]:
        """
        Capture current screen and return as base64-encoded JPEG + PIL Image.
        Thread-safe: Creates new MSS instance per call to avoid thread-local storage issues.

        Returns:
            Tuple of (base64_string, pil_image)
        """
        # Create fresh MSS instance to avoid thread-local storage issues with Gradio
        with mss.mss() as sct:
            # Capture based on mode
            if self.focus_mode:
                # TODO: In focus mode, we'd ideally capture just the active window
                # For now, still capture full monitor (would need platform-specific code)
                # On Linux: use xdotool/wmctrl, Windows: pywin32, macOS: AppKit
                monitor = sct.monitors[self.monitor_id]
            else:
                monitor = sct.monitors[self.monitor_id]

            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

            # Crop right side to exclude chat interface
            if self.crop_right_percent > 0:
                width, height = img.size
                crop_width = int(width * (1 - self.crop_right_percent / 100))
                img = img.crop((0, 0, crop_width, height))

            # Resize for efficiency
            img = img.resize((1440, 800), Image.Resampling.LANCZOS)

            # Convert to JPEG for API
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            img_b64 = base64.b64encode(buffered.getvalue()).decode()

            return img_b64, img

    def _manage_frame_buffer(self, new_frame: str):
        """
        Manage frame buffer based on vision_history_mode.
        
        Args:
            new_frame: Base64-encoded frame to add
        """
        if self.vision_history_mode == "clear":
            # Clear buffer each time, only keep current frame
            self.frame_buffer = [new_frame]
        elif self.vision_history_mode == "temporal":
            # Keep last N frames (sliding window)
            self.frame_buffer.append(new_frame)
            if len(self.frame_buffer) > self.context_frames:
                self.frame_buffer.pop(0)
        elif self.vision_history_mode == "keep":
            # Keep all frames (up to a reasonable limit to avoid memory issues)
            self.frame_buffer.append(new_frame)
            if len(self.frame_buffer) > 50:  # Safety limit
                self.frame_buffer.pop(0)

    async def analyze_frame(
        self,
        user_prompt: str = "Respond to user, prompt and activity on the screen",
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: int = 512,
        frequency_penalty: float = 0.9,  # Strong anti-repetition
        presence_penalty: float = 0.6,   # Moderate anti-repetition
        use_history: bool = True,
        check_duplicates: bool = False,  # Enable duplicate checking for monitoring
        skip_schedule_check: bool = False  # Skip schedule check (for user-initiated queries)
    ) -> Optional[str]:
        """
        Send current frame(s) to VLM for analysis with character personality.

        Args:
            user_prompt: What the user is asking/commenting
            stream: Whether to stream the response
            temperature: Sampling temperature (higher = more varied)
            max_tokens: Maximum response length
            frequency_penalty: Penalize token frequency (0.0-2.0)
            presence_penalty: Penalize tokens that appeared (0.0-2.0)
            use_history: Whether to include conversation history
            check_duplicates: Whether to check and skip duplicate messages
            skip_schedule_check: Skip schedule check (for manual queries)

        Returns:
            Character's response as string, or None if skipped
        """

        # Check schedule (only for auto-monitoring, not user queries)
        if not skip_schedule_check and not self.is_within_schedule():
            self.stats["frames_skipped_schedule"] += 1
            return None

        # Capture current frame
        frame_b64, frame_img = self.capture_frame()

        # Check for screen activity (skip if no change detected)
        has_activity, change_pct = self.detect_screen_activity(frame_img)
        if not has_activity:
            self.stats["frames_skipped_no_change"] += 1
            return None
        
        # Manage frame buffer based on vision mode
        self._manage_frame_buffer(frame_b64)

        # Build messages array
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Add conversation history (text only)
        if use_history and self.conversation_history:
            # Get recent history (last N exchanges)
            recent_history = self.conversation_history[-self.max_history:]
            messages.extend(recent_history)
        
        # Add current user message with image(s)
        # Build content with text and all frames from buffer
        content = [{"type": "text", "text": user_prompt}]
        
        # Add frames from buffer (most recent first if multiple)
        for frame in reversed(self.frame_buffer):
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame}"}
            })
        
        messages.append({
            "role": "user",
            "content": content
        })

        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stream=stream
            )

            if stream:
                full_response = ""
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        full_response += text
                        print(text, end="", flush=True)
                print()
                
                # Check for duplicates before storing
                if check_duplicates and self.is_duplicate_message(full_response):
                    self.stats["frames_skipped_duplicate"] += 1
                    return None  # Skip this message

                # Check trigger words (if set)
                if not self.check_trigger_words(full_response):
                    # Response doesn't contain trigger words, skip it
                    return None

                # Update stats
                self.stats["frames_analyzed"] += 1

                # Store in history (text only, not image)
                if use_history:
                    self.conversation_history.append({
                        "role": "user",
                        "content": user_prompt
                    })
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": full_response
                    })

                # Update last monitoring message
                if check_duplicates:
                    self.last_monitoring_message = full_response

                self.last_response = full_response
                return full_response
            else:
                text = response.choices[0].message.content

                # Check for duplicates before storing
                if check_duplicates and self.is_duplicate_message(text):
                    self.stats["frames_skipped_duplicate"] += 1
                    return None  # Skip this message

                # Check trigger words (if set)
                if not self.check_trigger_words(text):
                    # Response doesn't contain trigger words, skip it
                    return None

                # Update stats
                self.stats["frames_analyzed"] += 1

                # Store in history
                if use_history:
                    self.conversation_history.append({
                        "role": "user",
                        "content": user_prompt
                    })
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": text
                    })

                # Update last monitoring message
                if check_duplicates:
                    self.last_monitoring_message = text

                self.last_response = text
                return text

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            print(error_msg)
            return error_msg
    
    async def continuous_monitoring(
        self,
        base_prompt: str = "Observe and comment on what's happening",
        interval_seconds: Optional[float] = None,
        stats_interval: int = 20  # Show stats every N iterations
    ):
        """
        Continuously monitor screen at specified FPS with smarter detection.

        Args:
            base_prompt: Default prompt for observations
            interval_seconds: Override FPS with specific interval
            stats_interval: Show stats every N iterations (0 to disable)
        """
        self.running = True
        sleep_time = interval_seconds if interval_seconds else (1.0 / self.fps)
        iteration_count = 0

        print(f"👁️  Monitoring started ({self.fps} FPS)")
        if self.activity_detection:
            print(f"⚡ Activity detection enabled (threshold: {self.activity_threshold}%)")
        if self.schedule_start or self.schedule_end:
            start = self.schedule_start.strftime("%H:%M") if self.schedule_start else "none"
            end = self.schedule_end.strftime("%H:%M") if self.schedule_end else "none"
            print(f"⏰ Monitoring schedule: {start} - {end}")
        print("Press Ctrl+C to stop\n")

        try:
            while self.running:
                await self.analyze_frame(
                    user_prompt=base_prompt,
                    check_duplicates=True,  # Enable duplicate checking for monitoring
                    skip_schedule_check=False  # Respect schedule
                )

                iteration_count += 1

                # Show periodic stats
                if stats_interval > 0 and iteration_count % stats_interval == 0:
                    print(f"\n{self.get_stats_summary()}\n")

                await asyncio.sleep(sleep_time)
        except KeyboardInterrupt:
            print(f"\n⏸️  Monitoring stopped")
            print(f"{self.get_stats_summary()}")
            self.running = False

    def stop(self):
        """Stop monitoring and cleanup."""
        self.running = False


if __name__ == "__main__":
    async def demo():
        pipeline = StreamingVisionPipeline(
            character="maya", 
            fps=1.0, 
            context_frames=3,
            crop_right_percent=35.0,  # Exclude right 25%
            similarity_threshold=0.80  # Skip if >80% similar
        )
        
        # Test conversation
        print("\n=== Testing Conversation History ===\n")
        
        await pipeline.analyze_frame(user_prompt="What do you see on screen?")
        await asyncio.sleep(1)
        
        await pipeline.analyze_frame(user_prompt="What colors are visible?")
        await asyncio.sleep(1)
        
        await pipeline.analyze_frame(user_prompt="What did I ask you before this?")
        
        print(f"\n{pipeline.get_history_summary()}")
        
        pipeline.stop()
    
    asyncio.run(demo())
