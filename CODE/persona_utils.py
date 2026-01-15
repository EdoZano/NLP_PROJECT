"""Utility for loading story configuration.

Functions:
- load_story_config(): loads configuration JSON
"""

import json
import os


STORY_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "story_config.json")


def load_story_config():
    """Loads the complete story configuration from JSON file.
    
    Returns:
        dict containing: world, plot, characters, narrative_config
    """
    if not os.path.exists(STORY_CONFIG_PATH):
        raise FileNotFoundError(
            f"Configuration file not found: {STORY_CONFIG_PATH}\n"
            "Make sure story_config.json exists in the CODE directory."
        )
    
    print(f"[INFO] Loading configuration from: {STORY_CONFIG_PATH}")
    with open(STORY_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

