import random
import re
from typing import Tuple, List

def generate_random_color() -> str:
    """Generate a random hex color code"""
    return f"#{random.randint(0, 0xFFFFFF):06x}"

def parse_span_text(text: str, start_idx: int, end_idx: int) -> str:
    """Extract span of text given start and end indices"""
    return text[start_idx:end_idx]

def find_token_boundaries(text: str, approximate_start: int, approximate_end: int) -> Tuple[int, int]:
    """
    Find exact token boundaries given approximate indices
    
    Args:
        text: Input text
        approximate_start: Approximate start index
        approximate_end: Approximate end index
        
    Returns:
        Tuple of (exact_start, exact_end)
    """
    # Pattern for word boundaries
    word_pattern = r'\b\w+\b'
    
    # Find all word matches
    matches = list(re.finditer(word_pattern, text))
    
    # Find closest starting boundary
    start_idx = approximate_start
    for match in matches:
        if match.start() <= approximate_start <= match.end():
            start_idx = match.start()
            break
    
    # Find closest ending boundary
    end_idx = approximate_end
    for match in matches:
        if match.start() <= approximate_end <= match.end():
            end_idx = match.end()
            break
    
    return start_idx, end_idx

def validate_annotation_span(text: str, span: Tuple[int, int]) -> bool:
    """
    Validate if an annotation span is valid
    
    Args:
        text: Input text
        span: (start_idx, end_idx) tuple
        
    Returns:
        Boolean indicating if span is valid
    """
