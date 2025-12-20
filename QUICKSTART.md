# Quick Start Guide - Vision Assist

Get up and running in 5 minutes!

## 1. Prerequisites

```bash
# Install Python packages
pip install --break-system-packages mss pillow pyyaml openai

# Start vLLM server (required!)
vllm serve Qwen/Qwen3-VL-2B-Instruct --dtype auto --api-key dummy
```

## 2. Verify Installation

```bash
cd vision_assist

# Test character loading
python character_profiles_dynamic.py

# Expected output:
# ✓ Loaded character: Maya
# 🎭 Character System Ready - 1 character(s) available
```

## 3. Run Your First Session

### Option A: Easy Launcher (Recommended)

```bash
bash launcher.sh
```

Select mode 1 (Interactive) and character 1 (Maya).

### Option B: Direct Run

```bash
python interactive_vision_assistant.py --character maya
```

## 4. Try These Commands

```bash
# Ask about your screen
💬 ask what's on my screen?

# Start auto-monitoring
💬 auto

# Stop monitoring
💬 stop

# Check status
💬 status

# Clear conversation history
💬 clear

# Get help
💬 help

# Exit
💬 quit
```

## 5. Test Conversation Memory

```bash
💬 ask what do you see?
# Maya responds...

💬 ask what colors are visible?
# Maya responds...

💬 ask what did I ask before this?
# Maya should reference your previous questions! ✅
```

## Common First-Time Issues

### "vLLM server not running"

**Fix:**
```bash
vllm serve Qwen/Qwen3-VL-2B-Instruct --dtype auto --api-key dummy
```

Wait for the server to fully start (look for "Application startup complete").

### "No characters loaded"

**Fix:**
```bash
# Make sure chars directory exists
mkdir -p ./chars

# Copy the example character
# (maya.yaml should already be there)
ls ./chars/
```

### Repetitive Responses

**Fix:**
```bash
💬 freq 1.2
💬 pres 0.8
💬 clear
```

## Quick Tips

### Conversation History
- Automatically remembers last 10 exchanges
- Clear with `clear` command if it gets confused
- Check with `status` command

### Anti-Repetition
- Default settings prevent loops (freq=0.9, pres=0.6)
- Increase if still seeing repetition
- Decrease if responses are too random

### Vision Modes
- **clear** (default): Only sees current screen
- **temporal**: Knows about past screens tagged as [PAST]
- **keep**: Full visual history (uses more tokens)

Change with: `💬 visionmode temporal`

## Next Steps

1. **Read the full README** for all features
2. **Create custom characters** in `./chars/`
3. **Try auto-monitoring** mode for continuous feedback
4. **Adjust settings** to your preference

## Example Session

```bash
$ python interactive_vision_assistant.py --character maya

💬 ask hey maya, what's on my desktop?
Maya: Yo, I see you got a terminal open with some code...

💬 ask what programming language?
Maya: That's Python, looks like you're working with some async stuff.

💬 ask any suggestions?
Maya: Could clean up those variable names a bit, but looks solid overall.

💬 status
# Shows: History: 6 messages

💬 clear
# Clears conversation history

💬 quit
👋 Goodbye!
```

## Get Help

- Type `help` in the CLI
- Read README.md for detailed docs
- Check troubleshooting section

That's it! You're ready to use Vision Assist! 🎉
