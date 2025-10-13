import re
from typing import Tuple, Optional

def parse_name(full_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Parse a full name into first and last name.
    
    Args:
        full_name: The full name to parse
        
    Returns:
        A tuple of (first_name, last_name)
    """
    if not full_name or not isinstance(full_name, str):
        return None, None
    
    # Clean up the name
    name = full_name.strip()
    
    # Remove extra whitespace and special characters
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[^\w\s-]', '', name, flags=re.UNICODE)
    
    # Split into parts
    parts = name.split()
    
    if not parts:
        return None, None
    elif len(parts) == 1:
        return parts[0], None
    else:
        # First part is first name, last part is last name, middle names are part of first name
        first_name = ' '.join(parts[:-1])
        last_name = parts[-1]
        return first_name, last_name

def format_contributions(contributions: int) -> str:
    """Format the number of contributions for display."""
    if contributions >= 1000000:
        return f"{contributions/1000000:.1f}M"
    elif contributions >= 1000:
        return f"{contributions/1000:.1f}K"
    return str(contributions)

def get_github_avatar_url(username: str, size: int = 80) -> str:
    """Get the GitHub avatar URL for a username with optional size parameter."""
    return f"https://github.com/{username}.png?size={size}"

def get_github_profile_url(username: str) -> str:
    """Get the GitHub profile URL for a username."""
    return f"https://github.com/{username}"
