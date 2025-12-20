# character_profiles_fixed.py
"""
Simplified character profile system for vision assistant.
Dynamically loads all characters from ./chars/ directory.
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional


def load_character_config(file_path: str) -> Optional[dict]:
    """Load a character configuration from YAML file."""
    try:
        with open(file_path, "r") as file:
            config = yaml.safe_load(file)
            return config.get("character")
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        return None


def load_all_characters(chars_dir: str = "./chars") -> Dict[str, dict]:
    """
    Load all character configurations from the chars directory.
    
    Args:
        chars_dir: Path to directory containing character YAML files
        
    Returns:
        Dictionary mapping character keys to their configurations
    """
    chars_path = Path(chars_dir)
    characters = {}
    
    if not chars_path.exists():
        # Don't warn here - lazy loading will handle missing directory
        return characters
    
    # Load all .yaml and .yml files
    for yaml_file in chars_path.glob("*.yaml"):
        char_config = load_character_config(str(yaml_file))
        if char_config:
            # Use filename (without extension) as key
            char_key = yaml_file.stem.lower()
            characters[char_key] = char_config
            print(f"✓ Loaded character: {char_config.get('name', char_key)}")
    
    for yaml_file in chars_path.glob("*.yml"):
        char_config = load_character_config(str(yaml_file))
        if char_config:
            char_key = yaml_file.stem.lower()
            if char_key not in characters:  # Don't overwrite .yaml with .yml
                characters[char_key] = char_config
                print(f"✓ Loaded character: {char_config.get('name', char_key)}")
    
    return characters


def rate_content_disposition(level: int) -> str:
    """
    Define character's openness to mature/adult content discussion (1-5 scale).
    """
    dispositions = {
        1: "Strictly avoids mature content, maintaining a professional tone",
        2: "Cautious about mature content, preferring to redirect conversations",
        3: "Neutral stance on mature content, handles it when contextually relevant",
        4: "Open to discussing mature content appropriately, using a relaxed tone",
        5: "Comfortable with mature content discussions, using a casual tone",
    }
    return dispositions.get(level, "Invalid level")


def rate_language_disposition(level: int) -> str:
    """
    Define character's language formality level (1-5 scale).
    """
    dispositions = {
        1: "Strictly formal language, avoids colloquialisms",
        2: "Mostly formal, occasionally uses casual terms",
        3: "Balanced mix of formal and casual language",
        4: "Casual and informal language style",
        5: "Very casual, uses slang and colloquial expressions freely",
    }
    return dispositions.get(level, "Invalid level")


# Load all characters at module import
ALL_CHARACTERS = load_all_characters()

# Fallback to first available character if no characters loaded
DEFAULT_CHARACTER_KEY = list(ALL_CHARACTERS.keys())[0] if ALL_CHARACTERS else None


def format_character_prompt(character_dict: dict, include_desktop_context: bool = True) -> str:
    """
    Format character profile into a clean, focused system prompt.
    Handles various YAML field name variations.

    Args:
        character_dict: Character profile dictionary
        include_desktop_context: Add desktop observation instructions

    Returns:
        Formatted system prompt string
    """
    if not character_dict:
        raise ValueError("character_dict is None or empty!")
    
    c = character_dict
    
    # Validate required fields
    if not c.get('name'):
        raise ValueError("Character missing required field: 'name'")
    
    # Handle different field names for content disposition
    content_field = (c.get('content_disposition') or 
                     c.get('material_disposition') or '1')
    
    # Handle different field names for language formality
    language_field = (c.get('language_disposition') or '2')
    
    # Convert to int if it's a string
    try:
        content_level = int(str(content_field)[0])  # Get first char in case it's "1 - Description"
        language_level = int(str(language_field)[0])
    except (ValueError, IndexError):
        content_level = 1
        language_level = 2
    
    # Build core personality
    prompt = f"""
    """
    
    final_prompt = prompt.strip()
    
    # Validate prompt is not empty
    if not final_prompt or len(final_prompt) < 50:
        raise ValueError(f"Generated prompt is too short or empty! Length: {len(final_prompt)}")
    
    return final_prompt


def get_character_profiles() -> Dict[str, str]:
    """
    Get pre-formatted character prompts for all loaded characters.
    Auto-reloads if no characters are loaded.

    Returns:
        Dictionary of character_key -> formatted_prompt
    """
    global ALL_CHARACTERS
    
    # Lazy loading: if no characters loaded, try loading now
    if not ALL_CHARACTERS:
        print("⚠️  No characters loaded. Attempting to load from ./chars/...")
        reload_characters()
        
        if not ALL_CHARACTERS:
            raise ValueError(
                "No characters found!\n"
                "Make sure ./chars/ directory exists and contains .yaml files.\n"
                "Run: python diagnose_characters.py"
            )
    
    profiles = {}
    
    for key, char_dict in ALL_CHARACTERS.items():
        profiles[key] = format_character_prompt(char_dict)
        profiles[f"{key}_minimal"] = format_character_prompt(char_dict, include_desktop_context=False)
        profiles[f"{key}_dict"] = char_dict
    
    return profiles


def get_character_dict(name: str) -> Optional[dict]:
    """
    Get raw character dictionary by name.
    Auto-reloads if no characters are loaded.
    
    Args:
        name: Character key (filename without extension)
        
    Returns:
        Character dictionary or None if not found
    """
    global ALL_CHARACTERS
    
    # Lazy loading
    if not ALL_CHARACTERS:
        print("⚠️  No characters loaded. Attempting to load from ./chars/...")
        reload_characters()
    
    return ALL_CHARACTERS.get(name.lower())


def get_character_keys() -> List[str]:
    """Get list of all available character keys."""
    return list(ALL_CHARACTERS.keys())


def customize_character(base_character: dict, modifications: dict) -> str:
    """
    Create a customized character by modifying a profile.

    Args:
        base_character: Base profile dictionary
        modifications: Dictionary of fields to override

    Returns:
        Formatted prompt with customizations
    """
    import copy
    character = copy.deepcopy(base_character)
    character.update(modifications)
    return format_character_prompt(character)


def list_characters() -> List[dict]:
    """List available character profiles with their details."""
    return [
        {
            "name": char_dict.get("name", key),
            "key": key,
            "role": char_dict.get("role", "Unknown"),
            "age": char_dict.get("age", "N/A")
        }
        for key, char_dict in ALL_CHARACTERS.items()
    ]


def reload_characters(chars_dir: str = "./chars"):
    """
    Reload all character configurations from disk.
    Useful if character files have been modified or added after initial import.
    
    Args:
        chars_dir: Path to directory containing character YAML files
    """
    global ALL_CHARACTERS, DEFAULT_CHARACTER_KEY
    
    print("\n🔄 Reloading characters...")
    ALL_CHARACTERS = load_all_characters(chars_dir)
    DEFAULT_CHARACTER_KEY = list(ALL_CHARACTERS.keys())[0] if ALL_CHARACTERS else None
    
    if ALL_CHARACTERS:
        print(f"✓ Loaded {len(ALL_CHARACTERS)} character(s)")
        for key in ALL_CHARACTERS.keys():
            print(f"  - {key}")
    else:
        print("⚠️  No characters loaded!")
        print(f"   Check that {chars_dir} exists and contains .yaml files")
    print()


# Module-level info
if ALL_CHARACTERS:
    print(f"\n🎭 Character System Ready - {len(ALL_CHARACTERS)} character(s) available")
# No warning if empty - lazy loading will handle it when characters are needed


if __name__ == "__main__":
    print("=" * 70)
    print("Available Characters:")
    print("=" * 70)
    
    if not ALL_CHARACTERS:
        print("No characters found in ./chars/ directory")
    else:
        for char in list_characters():
            print(f"\n  Key: {char['key']}")
            print(f"  Name: {char['name']}")
            print(f"  Role: {char['role']}")
            print(f"  Age: {char['age']}")
        
        print("\n" + "=" * 70)
        print("Sample Prompt Preview (first character):")
        print("=" * 70)
        
        first_key = list(ALL_CHARACTERS.keys())[0]
        first_char = ALL_CHARACTERS[first_key]
        sample_prompt = format_character_prompt(first_char)
        print(sample_prompt[:500] + "...\n")
        
        print(f"Total prompt length: {len(sample_prompt)} characters (~{len(sample_prompt.split())} words)")
