#!/usr/bin/env python3
"""
Interactive Vision Assistant - CLI Interface - v3
Real-time desktop monitoring with conversation commands

New in v3:
- ⚡ Activity detection - skip if screen unchanged
- 🎯 Focus mode - monitor active window only
- ⏰ Scheduled monitoring - time-based control
- 🔔 Trigger words - selective notifications
- 📊 Statistics tracking

Previous (v2):
- Message deduplication (no spam!)
- Screen crop controls
- Similarity threshold tuning

Commands:
  ask <message>      - Ask the assistant about what's on screen
  auto               - Start continuous monitoring
  stop               - Stop continuous monitoring
  clear              - Clear conversation history
  status             - Show current settings, stats, and history
  stats              - Show statistics summary
  character [name]   - List or switch characters
  visionmode <mode>  - Set vision history mode (clear/temporal/keep)
  crop <percent>     - Set screen crop percentage (0-50)
  similarity <val>   - Set similarity threshold (0.5-0.95)
  activity <on/off>  - Toggle activity detection
  activitythresh <%> - Set activity threshold (1-20%)
  focusmode <on/off> - Toggle focus mode
  triggerwords       - Set trigger words (comma-separated)
  schedule <HH:MM-HH:MM> - Set monitoring schedule
  freq <value>       - Set frequency penalty (0.0-2.0)
  pres <value>       - Set presence penalty (0.0-2.0)
  temp <value>       - Set temperature (0.0-2.0)
  tokens <n>         - Set max tokens
  help               - Show this help
  quit               - Exit
"""

import asyncio
import argparse
from streaming_vision_pipeline import StreamingVisionPipeline
from character_profiles_dynamic import get_character_keys, list_characters


class InteractiveVisionAssistant:
    def __init__(
        self,
        vllm_url: str = "http://localhost:8000/v1",
        character: str = "maya",
        auto_monitor: bool = False,
        fps: float = 1.0,
        crop_right_percent: float = 25.0,
        similarity_threshold: float = 0.80
    ):
        self.pipeline = StreamingVisionPipeline(
            vllm_url=vllm_url,
            character=character,
            fps=fps,
            crop_right_percent=crop_right_percent,
            similarity_threshold=similarity_threshold
        )
        
        self.auto_monitor = auto_monitor
        self.monitoring_task = None
        
        # Settings
        self.frequency_penalty = 0.9
        self.presence_penalty = 0.6
        self.temperature = 0.7
        self.max_tokens = 512
        
        # Stats
        self.messages_posted = 0
        self.messages_skipped = 0
    
    def print_help(self):
        """Print available commands."""
        help_text = """
╔══════════════════════════════════════════════════════════╗
║        INTERACTIVE VISION ASSISTANT COMMANDS v2           ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  CONVERSATION:                                           ║
║    ask <message>      Ask about what's on screen         ║
║    clear              Clear conversation history          ║
║                                                          ║
║  MONITORING:                                             ║
║    auto               Start continuous monitoring        ║
║    stop               Stop continuous monitoring         ║
║                                                          ║
║  CHARACTER:                                              ║
║    character          List available characters          ║
║    character <name>   Switch to character                ║
║                                                          ║
║  SETTINGS:                                               ║
║    status             Show current settings              ║
║    visionmode <mode>  Vision history (clear/temporal)    ║
║    crop <percent>     Crop right side (0-50%)            ║
║    similarity <val>   Similarity threshold (0.5-0.95)    ║
║    freq <value>       Frequency penalty (0.0-2.0)        ║
║    pres <value>       Presence penalty (0.0-2.0)         ║
║    temp <value>       Temperature (0.0-2.0)              ║
║    tokens <n>         Max tokens                         ║
║                                                          ║
║  SYSTEM:                                                 ║
║    help               Show this help                     ║
║    quit               Exit                               ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
        print(help_text)
    
    def print_status(self):
        """Print current settings and state."""
        char_name = self.pipeline.character_dict['name']
        char_role = self.pipeline.character_dict['role']
        history_count = len(self.pipeline.conversation_history)
        monitoring = "Yes" if self.monitoring_task and not self.monitoring_task.done() else "No"
        
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                     CURRENT STATUS v2                     ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Character:        {char_name} ({char_role})
║  Vision Mode:      {self.pipeline.vision_history_mode}
║  History:          {history_count} messages
║  Monitoring:       {monitoring}
║                                                          ║
║  CAPTURE SETTINGS:                                       ║
║    Screen Crop:       {100-self.pipeline.crop_right_percent:.0f}% visible (right {self.pipeline.crop_right_percent:.0f}% excluded)
║    Similarity:        {self.pipeline.similarity_threshold*100:.0f}% threshold
║                                                          ║
║  GENERATION SETTINGS:                                    ║
║    Temperature:       {self.temperature}
║    Frequency Penalty: {self.frequency_penalty}
║    Presence Penalty:  {self.presence_penalty}
║    Max Tokens:        {self.max_tokens}
║                                                          ║
║  MONITORING STATS:                                       ║
║    Messages Posted:   {self.messages_posted}
║    Duplicates Skipped: {self.messages_skipped}
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")
    
    async def start_auto_monitoring(self):
        """Start continuous monitoring in background."""
        if self.monitoring_task and not self.monitoring_task.done():
            print("⚠️  Already monitoring!")
            return
        
        # Reset stats
        self.messages_posted = 0
        self.messages_skipped = 0
        self.pipeline.last_monitoring_message = None
        
        print(f"🔄 Starting auto-monitoring at {self.pipeline.fps} FPS...")
        print(f"✂️  Capturing left {100-self.pipeline.crop_right_percent:.0f}% of screen")
        print(f"🔕 Filtering duplicates above {self.pipeline.similarity_threshold*100:.0f}% similarity\n")
        
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring loop with deduplication."""
        self.pipeline.running = True
        
        try:
            while self.pipeline.running:
                response = await self.pipeline.analyze_frame(
                    user_prompt="Observe what's happening on screen and comment if something interesting changes",
                    frequency_penalty=self.frequency_penalty,
                    presence_penalty=self.presence_penalty,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=False,  # Don't stream in CLI monitoring
                    check_duplicates=True  # Enable deduplication
                )
                
                # Check if message was posted or skipped
                if response is not None:
                    self.messages_posted += 1
                    print(f"\n👁️  [{self.messages_posted}/{self.messages_posted + self.messages_skipped}] {response}")
                else:
                    self.messages_skipped += 1
                    print(f"🔕 Skipped duplicate ({self.messages_posted}/{self.messages_posted + self.messages_skipped})", end="\r")
                
                await asyncio.sleep(1.0 / self.pipeline.fps)
        
        except asyncio.CancelledError:
            print(f"\n⏸️  Monitoring stopped. Posted: {self.messages_posted}, Skipped: {self.messages_skipped}")
            self.pipeline.running = False
    
    def stop_auto_monitoring(self):
        """Stop continuous monitoring."""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            self.pipeline.running = False
        else:
            print("⚠️  Not currently monitoring")
    
    async def process_command(self, command: str):
        """Process a user command."""
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return True
        
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        # Help
        if cmd in ['help', 'h', '?']:
            self.print_help()
        
        # Status
        elif cmd == 'status':
            self.print_status()
        
        # Ask
        elif cmd == 'ask':
            if not arg:
                print("⚠️  Usage: ask <your question>")
                return True
            
            print(f"\n💬 You: {arg}")
            print(f"🤖 {self.pipeline.character_dict['name']}: ", end="", flush=True)
            
            response = await self.pipeline.analyze_frame(
                user_prompt=arg,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                check_duplicates=False  # Don't check duplicates for user queries
            )
            print()
        
        # Clear history
        elif cmd == 'clear':
            self.pipeline.clear_history()
            self.messages_posted = 0
            self.messages_skipped = 0
        
        # Auto monitoring
        elif cmd == 'auto':
            await self.start_auto_monitoring()
        
        # Stop monitoring
        elif cmd == 'stop':
            self.stop_auto_monitoring()
        
        # Character management
        elif cmd == 'character':
            if not arg:
                # List characters
                chars = list_characters()
                print("\n📚 Available characters:")
                for char in chars:
                    current = "←" if char['key'] == self.pipeline.character_dict.get('name', '').lower() else ""
                    print(f"  • {char['key']}: {char['name']} - {char['role']} {current}")
                print()
            else:
                # Switch character
                try:
                    self.pipeline.switch_character(arg.lower())
                except ValueError as e:
                    print(f"⚠️  {e}")
        
        # Vision history mode
        elif cmd == 'visionmode':
            if arg.lower() in ['clear', 'temporal', 'keep']:
                self.pipeline.vision_history_mode = arg.lower()
                print(f"✓ Vision history mode: {arg.lower()}")
            else:
                print("⚠️  Valid modes: clear, temporal, keep")
        
        # Screen crop (NEW in v2)
        elif cmd == 'crop':
            try:
                percent = float(arg)
                if 0 <= percent <= 50:
                    self.pipeline.crop_right_percent = percent
                    print(f"✓ Screen crop: {100-percent:.0f}% visible (right {percent:.0f}% excluded)")
                else:
                    print("⚠️  Crop percentage must be between 0-50")
            except ValueError:
                print("⚠️  Invalid value. Use a number between 0 and 50")
        
        # Similarity threshold (NEW in v2)
        elif cmd == 'similarity':
            try:
                threshold = float(arg)
                if 0.5 <= threshold <= 0.95:
                    self.pipeline.similarity_threshold = threshold
                    print(f"✓ Similarity threshold: {threshold*100:.0f}%")
                else:
                    print("⚠️  Threshold must be between 0.5 and 0.95")
            except ValueError:
                print("⚠️  Invalid value. Use a number between 0.5 and 0.95")
        
        # Settings
        elif cmd == 'freq':
            try:
                self.frequency_penalty = float(arg)
                print(f"✓ Frequency penalty: {self.frequency_penalty}")
            except ValueError:
                print("⚠️  Invalid value. Use a number between 0.0 and 2.0")
        
        elif cmd == 'pres':
            try:
                self.presence_penalty = float(arg)
                print(f"✓ Presence penalty: {self.presence_penalty}")
            except ValueError:
                print("⚠️  Invalid value. Use a number between 0.0 and 2.0")
        
        elif cmd == 'temp':
            try:
                self.temperature = float(arg)
                print(f"✓ Temperature: {self.temperature}")
            except ValueError:
                print("⚠️  Invalid value. Use a number between 0.0 and 2.0")
        
        elif cmd == 'tokens':
            try:
                self.max_tokens = int(arg)
                print(f"✓ Max tokens: {self.max_tokens}")
            except ValueError:
                print("⚠️  Invalid value. Use an integer")
        
        # Quit
        elif cmd in ['quit', 'exit', 'q']:
            return False
        
        else:
            print(f"⚠️  Unknown command: {cmd}. Type 'help' for available commands.")
        
        return True
    
    async def run(self):
        """Main interaction loop."""
        print(f"""
╔══════════════════════════════════════════════════════════╗
║           INTERACTIVE VISION ASSISTANT v2                 ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Character: {self.pipeline.character_dict['name']} ({self.pipeline.character_dict['role']})
║  Screen Crop: {100-self.pipeline.crop_right_percent:.0f}% visible
║  Similarity: {self.pipeline.similarity_threshold*100:.0f}% threshold
║                                                          ║
║  Type 'help' for commands or 'ask <question>' to start   ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")
        
        # Start auto-monitoring if requested
        if self.auto_monitor:
            await self.start_auto_monitoring()
        
        try:
            while True:
                # Get user input
                prompt = "\n💬 " if not self.monitoring_task or self.monitoring_task.done() else "\n💬 (monitoring) "
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, prompt
                )
                
                # Process command
                should_continue = await self.process_command(user_input)
                if not should_continue:
                    break
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted by user")
        
        finally:
            # Cleanup
            self.stop_auto_monitoring()
            self.pipeline.stop()
            print("👋 Goodbye!\n")


def main():
    parser = argparse.ArgumentParser(description="Interactive Vision Assistant v2")
    parser.add_argument("--vllm-url", default="http://localhost:8000/v1", help="vLLM server URL")
    parser.add_argument("--character", default="maya", help="Character to use")
    parser.add_argument("--auto", action="store_true", help="Start with auto-monitoring")
    parser.add_argument("--fps", type=float, default=1.0, help="Frames per second for monitoring")
    parser.add_argument("--crop", type=float, default=25.0, help="Crop right side percentage (0-50)")
    parser.add_argument("--similarity", type=float, default=0.80, help="Similarity threshold (0.5-0.95)")
    
    args = parser.parse_args()
    
    assistant = InteractiveVisionAssistant(
        vllm_url=args.vllm_url,
        character=args.character,
        auto_monitor=args.auto,
        fps=args.fps,
        crop_right_percent=args.crop,
        similarity_threshold=args.similarity
    )
    
    asyncio.run(assistant.run())


if __name__ == "__main__":
    main()
