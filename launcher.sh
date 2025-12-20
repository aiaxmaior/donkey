#!/bin/bash
# Vision Assistant Launcher
# Auto-detects characters and provides easy launch options

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           VISION ASSISTANT LAUNCHER                       ║${NC}"
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

# Scan for characters
echo -e "${YELLOW}Scanning for characters...${NC}"
CHARS_DIR="./chars"
if [ ! -d "$CHARS_DIR" ]; then
    echo -e "${RED}✗ Characters directory not found${NC}"
    echo -e "${YELLOW}Please create $CHARS_DIR and add character YAML files${NC}"
    exit 1
fi

# Find all yaml files
CHAR_FILES=($(find "$CHARS_DIR" -name "*.yaml" -o -name "*.yml"))
if [ ${#CHAR_FILES[@]} -eq 0 ]; then
    echo -e "${RED}✗ No character files found in $CHARS_DIR${NC}"
    echo -e "${YELLOW}Please add character YAML files to $CHARS_DIR${NC}"
    exit 1
fi

# Extract character names
CHAR_NAMES=()
for file in "${CHAR_FILES[@]}"; do
    basename=$(basename "$file" .yaml)
    basename=$(basename "$basename" .yml)
    CHAR_NAMES+=("$basename")
    echo -e "  ${GREEN}✓${NC} Found: $basename"
done
echo ""

# Choose mode
echo -e "${BLUE}Choose mode:${NC}"
echo "  1. Interactive mode (default)"
echo "  2. Auto-monitoring"
echo "  3. Custom"
echo ""
read -p "Select mode [1-3]: " mode_choice

case "$mode_choice" in
    1|"")
        # Interactive mode
        echo ""
        echo -e "${BLUE}Available characters:${NC}"
        for i in "${!CHAR_NAMES[@]}"; do
            echo "  $((i+1)). ${CHAR_NAMES[$i]}"
        done
        echo ""
        read -p "Select character [1-${#CHAR_NAMES[@]}]: " char_choice
        
        if [ -z "$char_choice" ]; then
            char_choice=1
        fi
        
        idx=$((char_choice-1))
        if [ $idx -lt 0 ] || [ $idx -ge ${#CHAR_NAMES[@]} ]; then
            echo -e "${RED}Invalid choice${NC}"
            exit 1
        fi
        
        selected_char="${CHAR_NAMES[$idx]}"
        echo ""
        echo -e "${GREEN}Starting interactive mode with character: $selected_char${NC}"
        echo ""
        
        python3 interactive_vision_assistant.py --character "$selected_char"
        ;;
    
    2)
        # Auto-monitoring
        echo ""
        echo -e "${BLUE}Available characters:${NC}"
        for i in "${!CHAR_NAMES[@]}"; do
            echo "  $((i+1)). ${CHAR_NAMES[$i]}"
        done
        echo ""
        read -p "Select character [1-${#CHAR_NAMES[@]}]: " char_choice
        
        if [ -z "$char_choice" ]; then
            char_choice=1
        fi
        
        idx=$((char_choice-1))
        if [ $idx -lt 0 ] || [ $idx -ge ${#CHAR_NAMES[@]} ]; then
            echo -e "${RED}Invalid choice${NC}"
            exit 1
        fi
        
        selected_char="${CHAR_NAMES[$idx]}"
        
        echo ""
        read -p "FPS (frames per second) [1.0]: " fps
        if [ -z "$fps" ]; then
            fps=1.0
        fi
        
        echo ""
        echo -e "${GREEN}Starting auto-monitoring with $selected_char at $fps FPS${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        echo ""
        
        python3 interactive_vision_assistant.py --character "$selected_char" --auto --fps "$fps"
        ;;
    
    3)
        # Custom
        echo ""
        read -p "Character name: " char_name
        read -p "FPS [1.0]: " fps
        read -p "vLLM URL [http://localhost:8000/v1]: " vllm_url
        read -p "Auto-monitor? [y/N]: " auto_monitor
        
        if [ -z "$fps" ]; then
            fps=1.0
        fi
        
        if [ -z "$vllm_url" ]; then
            vllm_url="http://localhost:8000/v1"
        fi
        
        extra_args=""
        if [[ "$auto_monitor" =~ ^[Yy]$ ]]; then
            extra_args="$extra_args --auto"
        fi
        
        echo ""
        echo -e "${GREEN}Starting with custom settings...${NC}"
        echo ""
        
        python3 interactive_vision_assistant.py --character "$char_name" --fps "$fps" --vllm-url "$vllm_url" $extra_args
        ;;
    
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
