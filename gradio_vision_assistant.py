#!/usr/bin/env python3
"""
Gradio Vision Assistant - Web Interface - FIXED VERSION v3
Beautiful web UI for the streaming desktop vision assistant

New in v3:
- ✅ Smarter monitoring with activity detection
- ✅ Focus mode controls
- ✅ Scheduled monitoring (time-based)
- ✅ Trigger word alerts
- ✅ Statistics dashboard

Previous (v2):
- ✅ Message deduplication during monitoring (no spam!)
- ✅ Screen crop controls (exclude chat from capture)
- ✅ Proper async/await handling with Gradio
- ✅ Real-time monitoring updates in UI using generators
- ✅ Better error handling
- ✅ Proper integration with vision_history_mode
"""

import gradio as gr
import asyncio
import base64
from io import BytesIO
from PIL import Image
import threading
from typing import Optional, List, Tuple
from datetime import datetime

from streaming_vision_pipeline import StreamingVisionPipeline
from character_profiles_dynamic import get_character_keys, list_characters


class GradioVisionAssistant:
    def __init__(self, vllm_url: str = "http://localhost:8000/v1", model_name: str = "Qwen3-VL-Thinking"):
        self.vllm_url = vllm_url
        self.model_name = model_name
        self.pipeline: Optional[StreamingVisionPipeline] = None
        self.monitoring_active = False
        
        # Settings
        self.current_character = "miku"
        self.user_context = None
        self.fps = 1
        self.context_frames = 1
        self.monitor_id = 1
        self.crop_right_percent = 25.0
        self.similarity_threshold = 0.80

        # NEW v3: Smarter monitoring settings
        self.activity_detection = True
        self.activity_threshold = 5.0
        self.focus_mode = False
        self.trigger_words = []
        self.schedule_start = None
        self.schedule_end = None

        # Generation settings
        self.frequency_penalty = 1.2
        self.presence_penalty = 0.6
        self.temperature = 0.7
        self.max_tokens = 512
        
        # Initialize pipeline
        self._init_pipeline()
    
    def _init_pipeline(self):
        """Initialize or reinitialize the pipeline."""
        if self.pipeline:
            self.pipeline.stop()

        self.pipeline = StreamingVisionPipeline(
            vllm_url=self.vllm_url,
            model_name=self.model_name,
            character=self.current_character,
            user_context=self.user_context,
            fps=self.fps,
            context_frames=self.context_frames,
            monitor_id=self.monitor_id,
            crop_right_percent=self.crop_right_percent,
            similarity_threshold=self.similarity_threshold,
            # NEW v3: Smarter monitoring
            activity_detection=self.activity_detection,
            activity_threshold=self.activity_threshold,
            focus_mode=self.focus_mode,
            trigger_words=self.trigger_words if self.trigger_words else None,
            schedule_start=self.schedule_start,
            schedule_end=self.schedule_end
        )
    
    def get_character_info(self) -> str:
        """Get current character info as formatted string."""
        if not self.pipeline:
            return "No character loaded"
        
        char_dict = self.pipeline.character_dict
        return f"**{char_dict['name']}** - {char_dict['role']}"
    
    def get_current_screen(self) -> Image.Image:
        """Capture and return current screen as PIL Image."""
        if not self.pipeline:
            return None

        try:
            frame_b64, frame_img = self.pipeline.capture_frame()
            return frame_img
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None
    
    async def send_message(
        self,
        message: str,
        history: List[dict]
    ) -> Tuple[List[dict], str]:
        """
        Send a message and get response.
        
        Args:
            message: User's message
            history: Chat history in Gradio messages format
        
        Returns:
            Updated history and empty string (to clear input)
        """
        if not message.strip():
            return history, ""
        
        # Add user message to history
        history.append({"role": "user", "content": message})
        
        try:
            # Get response from pipeline (no duplicate checking for user messages)
            response = await self.pipeline.analyze_frame(
                user_prompt=message,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=False,
                check_duplicates=False  # Don't check duplicates for user queries
            )
            
            # Add assistant response to history
            if response:  # Should always have a response for user queries
                history.append({"role": "assistant", "content": response})
        except Exception as e:
            history.append({"role": "assistant", "content": f"❌ Error: {str(e)}"})
        
        return history, ""
    
    def clear_history(self) -> Tuple[List, str]:
        """Clear conversation history."""
        if self.pipeline:
            self.pipeline.clear_history()
        return [], "✅ Conversation history cleared"
    
    def switch_character(self, character_key: str) -> str:
        """Switch to a different character."""
        try:
            self.current_character = character_key
            self._init_pipeline()
            return f"✅ Switched to: {self.pipeline.character_dict['name']}"
        except Exception as e:
            return f"❌ Error switching character: {str(e)}"
    
    def update_settings(
        self,
        freq: float,
        pres: float,
        temp: float,
        tokens: int,
        fps: float,
        context_frames: int,
        monitor_id: int,
        user_context: str,
        vision_mode: str,
        crop_percent: float,
        similarity_threshold: float,
        # NEW v3: Smarter monitoring
        activity_detection: bool,
        activity_threshold: float,
        focus_mode: bool,
        trigger_words_str: str,
        schedule_start: str,
        schedule_end: str
    ) -> str:
        """Update generation and monitoring settings."""
        self.frequency_penalty = freq
        self.presence_penalty = pres
        self.temperature = temp
        self.max_tokens = tokens
        self.fps = fps
        self.context_frames = context_frames
        self.monitor_id = monitor_id
        self.user_context = user_context if user_context.strip() else None
        self.crop_right_percent = crop_percent
        self.similarity_threshold = similarity_threshold

        # NEW v3: Smarter monitoring settings
        self.activity_detection = activity_detection
        self.activity_threshold = activity_threshold
        self.focus_mode = focus_mode
        self.trigger_words = [w.strip() for w in trigger_words_str.split(',') if w.strip()]
        self.schedule_start = schedule_start if schedule_start.strip() else None
        self.schedule_end = schedule_end if schedule_end.strip() else None

        # Reinitialize pipeline with new settings
        self._init_pipeline()

        # Set vision mode
        if self.pipeline:
            self.pipeline.vision_history_mode = vision_mode

        return "✅ Settings updated"
    
    def get_status(self) -> str:
        """Get current status as formatted markdown."""
        if not self.pipeline:
            return "**No pipeline initialized**"
        
        char_name = self.pipeline.character_dict['name']
        char_role = self.pipeline.character_dict['role']
        history_count = len(self.pipeline.conversation_history) if hasattr(self.pipeline, 'conversation_history') else 0
        frame_count = len(self.pipeline.frame_buffer) if hasattr(self.pipeline, 'frame_buffer') else 0
        monitoring = "🟢 Active" if self.monitoring_active else "🔴 Inactive"
        
        # Get statistics
        stats_str = self.pipeline.get_stats_summary() if hasattr(self.pipeline, 'get_stats_summary') else "Stats not available"

        status = f"""### Current Status

**Model:** {self.model_name}
**Character:** {char_name} ({char_role})
**Monitor:** Display {self.monitor_id}
**Context Frames:** {self.context_frames}
**Vision Mode:** {self.pipeline.vision_history_mode}
**Frame Buffer:** {frame_count} frames
**History:** {history_count} messages
**Monitoring:** {monitoring}

**Capture Settings:**
- Screen Crop: {100-self.crop_right_percent:.0f}% visible (excluding right {self.crop_right_percent:.0f}%)
- Similarity Threshold: {self.similarity_threshold*100:.0f}%

**Smarter Monitoring:**
- Activity Detection: {"✅ ON" if self.activity_detection else "❌ OFF"} (threshold: {self.activity_threshold}%)
- Focus Mode: {"✅ ON" if self.focus_mode else "❌ OFF"}
- Trigger Words: {', '.join(self.trigger_words) if self.trigger_words else "None"}
- Schedule: {self.schedule_start or "none"} - {self.schedule_end or "none"}

**Generation Settings:**
- Temperature: {self.temperature}
- Frequency Penalty: {self.frequency_penalty}
- Presence Penalty: {self.presence_penalty}
- Max Tokens: {self.max_tokens}
- FPS: {self.fps}

{stats_str}
"""
        return status
    
    async def start_monitoring_generator(self, history: List[dict]):
        """
        Start auto-monitoring mode with proper UI updates using generator.
        This yields updates so Gradio can display them in real-time.
        Includes deduplication to prevent spam.
        """
        if self.monitoring_active:
            history.append({
                "role": "assistant",
                "content": "⚠️ Already monitoring!"
            })
            yield history, "⚠️ Already monitoring!"
            return
        
        self.monitoring_active = True
        
        # Reset last monitoring message for fresh start
        if self.pipeline:
            self.pipeline.last_monitoring_message = None
        
        # Add system message
        timestamp = datetime.now().strftime("%H:%M:%S")
        history.append({
            "role": "assistant",
            "content": f"🤖 System [{timestamp}]: Started auto-monitoring at {self.fps} FPS. Capturing left {100-self.crop_right_percent:.0f}% of screen. Duplicate messages will be filtered."
        })
        yield history, "🟢 Monitoring started"
        
        skipped_count = 0
        message_count = 0
        
        try:
            # Monitoring loop
            while self.monitoring_active:
                try:
                    # Generate observation (with duplicate checking enabled)
                    response = await self.pipeline.analyze_frame(
                        user_prompt="Observe what's happening on screen and comment if something interesting or different appears",
                        frequency_penalty=self.frequency_penalty,
                        presence_penalty=self.presence_penalty,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        stream=False,
                        check_duplicates=True  # Enable duplicate detection for monitoring
                    )
                    
                    # Only add to history if not a duplicate (response will be None if skipped)
                    if response is not None:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        history.append({
                            "role": "assistant",
                            "content": f"👁️ [{timestamp}]: {response}"
                        })
                        message_count += 1
                        
                        # Yield update to Gradio
                        status_msg = f"🟢 Monitoring... ({message_count} msgs, {skipped_count} skipped)"
                        yield history, status_msg
                    else:
                        # Message was skipped as duplicate
                        skipped_count += 1
                        # Update status without adding message
                        status_msg = f"🟢 Monitoring... ({message_count} msgs, {skipped_count} skipped)"
                        yield history, status_msg
                    
                    # Wait for next frame
                    await asyncio.sleep(1.0 / self.fps)
                    
                except Exception as e:
                    error_msg = f"❌ Error during monitoring: {str(e)}"
                    history.append({
                        "role": "assistant",
                        "content": error_msg
                    })
                    yield history, error_msg
                    break
        
        finally:
            self.monitoring_active = False
            timestamp = datetime.now().strftime("%H:%M:%S")
            history.append({
                "role": "assistant",
                "content": f"🤖 System [{timestamp}]: Monitoring stopped. Posted {message_count} messages, filtered {skipped_count} duplicates."
            })
            yield history, "🔴 Monitoring stopped"
    
    def stop_monitoring(self) -> str:
        """Stop auto-monitoring."""
        if not self.monitoring_active:
            return "⚠️ Not currently monitoring"
        
        self.monitoring_active = False
        return "🔴 Stopping monitoring..."


def create_gradio_interface(
    vllm_url: str = "http://localhost:8000/v1",
    model_name: str = "Qwen3-VL-Thinking"
):
    """Create the Gradio interface."""
    
    assistant = GradioVisionAssistant(vllm_url=vllm_url, model_name=model_name)
    
    # Get available characters
    try:
        characters = get_character_keys()
    except:
        characters = ["default"]
    
    # Create the interface
    with gr.Blocks(title="Vision Assistant") as demo:
        gr.Markdown("""
        # 🤖 Vision Assistant
        *Desktop monitoring with AI character personalities*
        """)
        
        with gr.Row():
            # Left column - Chat
            with gr.Column(scale=2):
                gr.Markdown("### 💬 Chat")
                chatbot = gr.Chatbot(   
                    label="Conversation",
                    height=1000,
                    type="messages"
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Message",
                        placeholder="Ask about what's on screen...",
                        show_label=False,
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Clear History", size="sm")
                    start_monitor_btn = gr.Button("▶️ Start Monitoring", size="sm", variant="secondary")
                    stop_monitor_btn = gr.Button("⏹️ Stop Monitoring", size="sm")
                
                # Character display
                character_display = gr.Markdown(assistant.get_character_info())
            
            # Right column - Settings & Preview
            with gr.Column(scale=1):
                # Screen preview
                gr.Markdown("### 📺 Current Screen")
                screen_preview = gr.Image(
                    label="Screen Preview",
                    show_label=False,
                    height=300
                )
                refresh_screen_btn = gr.Button("🔄 Refresh Screen", size="sm")
                
                # Character selector
                gr.Markdown("### 🎭 Character")
                character_selector = gr.Dropdown(
                    choices=characters,
                    value=assistant.current_character,
                    label="Select Character",
                    interactive=True
                )
                
                # Settings accordion
                with gr.Accordion("⚙️ Settings", open=False):
                    # Vision settings
                    gr.Markdown("**Vision Settings**")
                    
                    vision_mode_dropdown = gr.Dropdown(
                        choices=["clear", "temporal", "keep"],
                        value="clear",
                        label="Vision History Mode",
                        info="clear=new frame each time, temporal=sliding window, keep=accumulate"
                    )
                    
                    crop_slider = gr.Slider(
                        minimum=0,
                        maximum=50,
                        value=assistant.crop_right_percent,
                        step=5,
                        label="Crop Right Side (%)",
                        info="Exclude right portion of screen (prevents AI from seeing chat)"
                    )
                    
                    similarity_slider = gr.Slider(
                        minimum=0.5,
                        maximum=0.95,
                        value=assistant.similarity_threshold,
                        step=0.05,
                        label="Similarity Threshold",
                        info="Skip monitoring messages above this similarity (0.8 = 80% similar)"
                    )
                    
                    context_frames_slider = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=assistant.context_frames,
                        step=1,
                        label="Context Frames",
                        info="Number of recent frames to keep in context"
                    )
                    
                    # Generation settings
                    gr.Markdown("**Generation Settings**")
                    
                    freq_slider = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=assistant.frequency_penalty,
                        step=0.1,
                        label="Frequency Penalty (anti-repetition)"
                    )
                    
                    pres_slider = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=assistant.presence_penalty,
                        step=0.1,
                        label="Presence Penalty (anti-repetition)"
                    )
                    
                    temp_slider = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=assistant.temperature,
                        step=0.1,
                        label="Temperature (creativity)"
                    )
                    
                    tokens_slider = gr.Slider(
                        minimum=128,
                        maximum=1024,
                        value=assistant.max_tokens,
                        step=128,
                        label="Max Tokens"
                    )
                    
                    # Monitoring settings
                    gr.Markdown("**Monitoring Settings**")
                    
                    fps_slider = gr.Slider(
                        minimum=0.1,
                        maximum=5.0,
                        value=assistant.fps,
                        step=0.1,
                        label="Monitoring FPS"
                    )
                    
                    monitor_id_slider = gr.Slider(
                        minimum=1,
                        maximum=4,
                        value=assistant.monitor_id,
                        step=1,
                        label="Monitor ID",
                        info="Which display to capture (1=primary)"
                    )
                    
                    user_context_text = gr.Textbox(
                        value=assistant.user_context or "",
                        label="User Context",
                        placeholder="Optional: Add context about yourself for the AI...",
                        lines=3
                    )

                    # NEW v3: Smarter Monitoring Settings
                    gr.Markdown("**⚡ Smarter Monitoring (v3)**")

                    activity_detection_check = gr.Checkbox(
                        value=assistant.activity_detection,
                        label="Activity Detection",
                        info="Only analyze when screen changes significantly"
                    )

                    activity_threshold_slider = gr.Slider(
                        minimum=1.0,
                        maximum=20.0,
                        value=assistant.activity_threshold,
                        step=0.5,
                        label="Activity Threshold (%)",
                        info="Minimum % of pixels that must change"
                    )

                    focus_mode_check = gr.Checkbox(
                        value=assistant.focus_mode,
                        label="Focus Mode",
                        info="Only monitor active window (experimental)"
                    )

                    trigger_words_text = gr.Textbox(
                        value=", ".join(assistant.trigger_words) if assistant.trigger_words else "",
                        label="Trigger Words",
                        placeholder="word1, word2, word3 (comma-separated)",
                        info="Only notify when these words appear in response"
                    )

                    schedule_start_text = gr.Textbox(
                        value=assistant.schedule_start or "",
                        label="Schedule Start (HH:MM)",
                        placeholder="09:00",
                        info="Start monitoring at this time (24h format)"
                    )

                    schedule_end_text = gr.Textbox(
                        value=assistant.schedule_end or "",
                        label="Schedule End (HH:MM)",
                        placeholder="17:00",
                        info="Stop monitoring at this time (24h format)"
                    )

                    apply_settings_btn = gr.Button("Apply Settings", variant="secondary")
                
                # Status display
                with gr.Accordion("📊 Status", open=True):
                    status_display = gr.Markdown(assistant.get_status())
                    refresh_status_btn = gr.Button("🔄 Refresh Status", size="sm")
        
        # Status message area
        status_msg = gr.Textbox(label="Status", show_label=False, interactive=False)
        
        # Footer
        gr.Markdown("""
        ---
        **Tips:**
        - **Screen Crop**: Set to 25-30% to exclude this chat interface from captures (prevents AI from seeing its own messages!)
        - **Similarity Threshold**: Higher values (0.85-0.90) = stricter duplicate filtering
        - **Vision modes**: `clear` = fresh frame each time, `temporal` = sliding window of frames, `keep` = accumulate all frames
        - Increase penalties if responses get repetitive
        - Auto-monitoring now filters duplicate observations automatically
        """)
        
        # Event handlers with proper async handling
        
        # Send message - using Gradio's native async support
        send_btn.click(
            fn=assistant.send_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        msg_input.submit(
            fn=assistant.send_message,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        # Clear history
        clear_btn.click(
            fn=assistant.clear_history,
            outputs=[chatbot, status_msg]
        )
        
        # Refresh screen
        refresh_screen_btn.click(
            fn=assistant.get_current_screen,
            outputs=screen_preview
        )
        
        # Character selection
        def on_character_change(char_key):
            msg = assistant.switch_character(char_key)
            char_info = assistant.get_character_info()
            return char_info, msg
        
        character_selector.change(
            fn=on_character_change,
            inputs=character_selector,
            outputs=[character_display, status_msg]
        )
        
        # Apply settings
        apply_settings_btn.click(
            fn=assistant.update_settings,
            inputs=[
                freq_slider,
                pres_slider,
                temp_slider,
                tokens_slider,
                fps_slider,
                context_frames_slider,
                monitor_id_slider,
                user_context_text,
                vision_mode_dropdown,
                crop_slider,
                similarity_slider,
                # NEW v3: Smarter monitoring inputs
                activity_detection_check,
                activity_threshold_slider,
                focus_mode_check,
                trigger_words_text,
                schedule_start_text,
                schedule_end_text
            ],
            outputs=status_msg
        )
        
        # Monitoring controls - using generator for real-time updates
        start_monitor_btn.click(
            fn=assistant.start_monitoring_generator,
            inputs=chatbot,
            outputs=[chatbot, status_msg]
        )
        
        stop_monitor_btn.click(
            fn=assistant.stop_monitoring,
            outputs=status_msg
        )
        
        # Refresh status
        refresh_status_btn.click(
            fn=assistant.get_status,
            outputs=status_display
        )
        
        # Load screen on startup
        demo.load(
            fn=assistant.get_current_screen,
            outputs=screen_preview
        )
    
    return demo


def main():
    """Launch the Gradio interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gradio Vision Assistant")
    parser.add_argument("--vllm-url", default="http://localhost:8000/v1", help="vLLM server URL")
    parser.add_argument("--model-name", default="Qwen3-VL-Thinking", help="Model name")
    parser.add_argument("--share", action="store_true", help="Create public share link")
    parser.add_argument("--server-name", default="0.0.0.0", help="Server name")
    parser.add_argument("--server-port", type=int, default=7860, help="Server port")
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║         VISION ASSIST - GRADIO WEB INTERFACE v2          ║
╚══════════════════════════════════════════════════════════╝

Model: {args.model_name}
vLLM URL: {args.vllm_url}
Starting Gradio interface on port {args.server_port}...

New Features:
✅ Message deduplication (no more spam!)
✅ Screen crop controls (exclude chat from capture)
✅ Similarity threshold controls
""")
    
    demo = create_gradio_interface(vllm_url=args.vllm_url, model_name=args.model_name)
    
    demo.queue()  # Enable queueing for async operations and streaming
    demo.launch(
        share=args.share,
        server_name=args.server_name,
        server_port=args.server_port,
        show_error=True
    )


if __name__ == "__main__":
    main()
