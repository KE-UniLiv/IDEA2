"""

This module provides the functionality for reading personas and user stories from files.

"""

import pandas as pd

# From https://github.com/KE-UniLiv/askcq/blob/main/askcq/config.py
MAPPING = {
    1: "HA-1",
    2: "HA-2",
    3: "Pattern",
    4: "GPT4.1",
    5: "Gemini 2.5 Pro",
}

def personas_user_stories_to_string(file_path: str) -> str:
    """
    Read personas and user stories from a markdown file and return the content as a string.

    Args:
        file_path (str): The path to the markdown file containing personas and user stories.
    
    Returns:
        str: The content of the markdown file as a string.

    """
    with open(file_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    return md_text



