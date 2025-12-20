#!/bin/bash
# Gradio Vision Assistant Launcher
# Simple launcher for the web interface

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       VISION ASSIST - GRADIO WEB INTERFACE               ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check for vLLM server
echo -e "${YELLOW}Checking vLLM server...${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ vLLM server is running${NC}"
else
    echo -e "${RED}✗ vLLM server is not running${NC}"
    echo -e "${YELLOW}Please start vLLM server first:${NC}"
    echo "  vllm serve Qwen/Qwen3-VL-2B-Instruct --dtype auto --api-key dummy"
    exit 1
fi
echo ""

# Check for characters
echo -e "${YELLOW}Checking characters...${NC}"
CHARS_DIR="./chars"
if [ ! -d "$CHARS_DIR" ]; then
    echo -e "${RED}✗ Characters directory not found${NC}"
    exit 1
fi

CHAR_COUNT=$(find "$CHARS_DIR" -name "*.yaml" -o -name "*.yml" | wc -l)
if [ $CHAR_COUNT -eq 0 ]; then
    echo -e "${RED}✗ No character files found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found $CHAR_COUNT character(s)${NC}"
echo ""

# Check for gradio
echo -e "${YELLOW}Checking Gradio installation...${NC}"
if python3 -c "import gradio" 2>/dev/null; then
    echo -e "${GREEN}✓ Gradio is installed${NC}"
else
    echo -e "${RED}✗ Gradio is not installed${NC}"
    echo -e "${YELLOW}Install with: pip install gradio${NC}"
    exit 1
fi
echo ""

# Get configuration
echo -e "${BLUE}Configuration:${NC}"
read -p "Port [7860]: " port

# Set defaults
if [ -z "$port" ]; then
    port=7860
fi

extra_args=""
if [[ "$share_choice" =~ ^[Yy]$ ]]; then
    extra_args="$extra_args --share"
fi

echo ""
echo -e "${GREEN}Starting Gradio interface...${NC}"
echo -e "${BLUE}Open your browser to: http://localhost:$port${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Launch
python3 gradio_vision_assistant.py --server-port "$port" $extra_args
