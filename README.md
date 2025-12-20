# Vision Assist - Streaming Desktop Vision Pipeline

Real-time desktop monitoring with VLM-powered AI assistants that have personality!

## What This Project Does

Vision Assist creates an AI assistant that watches your desktop in real-time and responds with personality. Perfect for:

- **Stable Diffusion workflows** - Get real-time feedback on your generations
- **Coding sessions** - Have an AI pair programmer watch over your shoulder
- **Creative work** - Get instant critiques and suggestions
- **Debugging** - Catch issues as they happen
- **Learning** - Ask questions about what you're seeing on screen

## Key Features

### ✅ Fixed from Previous Version

- **Conversation History**: Characters now remember your conversation context
- **No More Repetition**: Strong anti-repetition penalties prevent loops
- **Dynamic Character Loading**: Just drop YAML files in `./chars/` - no code changes needed
- **Vision History Modes**: Control how the AI handles previous visual descriptions
- **Interactive CLI**: Easy-to-use command interface

### 🎭 Character System

Characters are defined in simple YAML files:

```bash
./chars/
├── maya.yaml    # Sassy tech-savvy assistant (included)
├── miku.yaml    # Your custom character
└── alex.yaml    # Another custom character
```

No code changes needed - just add YAML files and they're automatically detected!

### 💬 Conversation Memory

```python
You: what do you see?
Maya: I see a terminal with system stats...

You: what colors?
Maya: Dark blue background with bright green text...

You: what did I ask before this?
Maya: You asked about the colors on screen.  # ✅ Remembers context!
```

## Quick Start

### 1. Requirements

```bash
# Python packages
pip install --break-system-packages mss pillow pyyaml openai

# vLLM server (must be running)
vllm serve Qwen/Qwen3-VL-2B-Instruct --dtype auto --api-key dummy
```

### 2. Installation

```bash
# Clone or download this project
cd vision_assist

# Verify character loading
python character_profiles_dynamic.py

# Should see:
# ✓ Loaded character: Maya
# 🎭 Character System Ready - 1 character(s) available
```

### 3. Run

```bash
# Easy launcher (recommended)
bash launcher.sh

# Or run directly
python interactive_vision_assistant.py --character maya
```

## Usage

### Interactive Mode

```bash
$ python interactive_vision_assistant.py --character maya

💬 ask what's on my screen right now?
💬 clear                 # Clear conversation history
💬 status                # Show current settings
💬 character miku        # Switch to another character
💬 help                  # Show all commands
💬 quit                  # Exit
```

### Auto-Monitoring Mode

```bash
# Continuous monitoring at 1 FPS
python interactive_vision_assistant.py --character maya --auto --fps 1.0

# Maya will continuously observe and comment
# Press Ctrl+C to stop
```

### Available Commands

| Command | Description |
|---------|-------------|
| `ask <message>` | Ask about what's on screen |
| `auto` | Start continuous monitoring |
| `stop` | Stop monitoring |
| `clear` | Clear conversation history |
| `status` | Show settings and history |
| `character [name]` | List or switch characters |
| `visionmode <mode>` | Set vision history mode |
| `freq <value>` | Set frequency penalty (0.0-2.0) |
| `pres <value>` | Set presence penalty (0.0-2.0) |
| `temp <value>` | Set temperature (0.0-2.0) |
| `tokens <n>` | Set max tokens |
| `help` | Show help |
| `quit` | Exit |

## Creating Custom Characters

Create a new file in `./chars/yourcharacter.yaml`:

```yaml
character:
  name: Your Character Name
  age: N/A
  role: What they do
  
  background: |
    Character backstory and personality description.
  
  content_disposition: 1      # 1-5: openness to mature content (1=strict, 5=casual)
  language_disposition: 2     # 1-5: language formality (1=formal, 5=casual/slang)
  
  traits: Personality traits comma-separated
  
  communication_style: |
    How the character speaks and expresses themselves.
  
  knowledge: |
    What areas the character is knowledgeable about.
  
  loves: What they enjoy
  dislikes: What they don't like
  excited_by: What excites them
  uncomfortable_with: What bothers them
  
  response_patterns: |
    Example responses that show their style.
  
  watching_because: |
    Why they're observing the desktop.
```

Then just use it:

```bash
python interactive_vision_assistant.py --character yourcharacter
```

## Configuration

### Vision History Modes

- **clear** (default): Ignore previous visual descriptions, only see current screen
- **temporal**: Tag old descriptions as [PAST SCREEN] for temporal awareness
- **keep**: Include all visual history (uses more tokens)

### Anti-Repetition Settings

Default values (optimized to prevent loops):

- **Frequency Penalty**: 0.9 (prevents word repetition)
- **Presence Penalty**: 0.6 (prevents phrase repetition)
- **Temperature**: 0.7 (balanced creativity)

Adjust with commands:
```bash
💬 freq 1.2    # Stronger anti-repetition
💬 pres 0.8    # Even stronger
💬 temp 0.5    # More focused responses
```

## File Structure

```
vision_assist/
├── streaming_vision_pipeline.py    # Core pipeline with history
├── interactive_vision_assistant.py # CLI interface
├── character_profiles_dynamic.py   # Character loader
├── launcher.sh                     # Easy launcher script
├── chars/                          # Character directory
│   └── maya.yaml                   # Example character
└── README.md                       # This file
```

## Programmatic Usage

```python
from streaming_vision_pipeline import StreamingVisionPipeline
import asyncio

async def main():
    # Create pipeline
    pipeline = StreamingVisionPipeline(
        character="maya",
        fps=1.0,
        vision_history_mode="clear"
    )
    
    # Ask a question
    response = await pipeline.analyze_frame(
        user_prompt="What's on screen?",
        frequency_penalty=0.9,
        presence_penalty=0.6
    )
    
    # Follow-up question (uses history!)
    response2 = await pipeline.analyze_frame(
        user_prompt="What do you mean by that?"
    )
    
    # Clear if needed
    pipeline.clear_history()
    
    # Cleanup
    pipeline.stop()

asyncio.run(main())
```

## Troubleshooting

### "No characters loaded"

1. Check that `./chars/` directory exists
2. Verify you have at least one `.yaml` or `.yml` file in `./chars/`
3. Test loading: `python character_profiles_dynamic.py`

### "vLLM server not running"

Start the vLLM server:
```bash
vllm serve Qwen/Qwen3-VL-2B-Instruct --dtype auto --api-key dummy
```

### Still seeing repetition?

Increase penalties:
```bash
💬 freq 1.2
💬 pres 0.8
```

Or clear history and start fresh:
```bash
💬 clear
```

### Responses too random?

Lower penalties:
```bash
💬 freq 0.5
💬 pres 0.3
💬 temp 0.5
```

### Character not remembering conversation?

Check history:
```bash
💬 status
# Should show "History: X messages"
```

If showing 0 messages, conversation history might be disabled. This version enables it by default.

## Technical Details

### Conversation History

The system maintains a conversation history of the last 10 exchanges (20 messages):

```python
messages = [
    {"role": "system", "content": CHARACTER_PROMPT},
    # Previous exchanges (text only):
    {"role": "user", "content": "previous question"},
    {"role": "assistant", "content": "previous answer"},
    # Current message (with image):
    {"role": "user", "content": [
        {"type": "text", "text": "current question"},
        {"type": "image_url", "image_url": {"url": "..."}}
    ]}
]
```

Images are only attached to the current message to save memory/tokens.

### Vision History Modes

- **clear**: Adds instruction to ignore previous visual descriptions
- **temporal**: Tags old visual descriptions as [PAST SCREEN]
- **keep**: Includes all previous messages as-is

## What's New

### Version 2.0 - October 2025

- ✅ Full conversation history (10 exchanges)
- ✅ Strong anti-repetition penalties by default
- ✅ Dynamic character loading from `./chars/`
- ✅ Vision history modes (clear/temporal/keep)
- ✅ Interactive CLI with commands
- ✅ Easy launcher script
- ✅ Comprehensive documentation

### Fixed Issues

1. **No conversation memory** → Full history support
2. **Stuck in repetition loops** → Strong penalties + clear mode
3. **Hardcoded characters** → Dynamic YAML-based loading
4. **Ghost images issue** → Vision history modes
5. **Character loading failures** → Lazy loading with validation

## Credits

Built with:
- **vLLM** - Fast inference server
- **Qwen3-VL** - Vision-language model
- **MSS** - Screen capture
- **OpenAI API format** - Easy integration

## License

MIT License - Feel free to use and modify!

## Need Help?

1. Check the troubleshooting section above
2. Verify vLLM server is running
3. Test character loading: `python character_profiles_dynamic.py`
4. Check conversation history: `status` command

Enjoy your AI assistant! 🎭
