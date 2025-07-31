"""

Utility functions for generation numbers i.e gxx_cqs.

"""


import os
import re

def get_generation_number() -> str:
    """
    Get the next generation number for the competency questions.

    This function scans the 'assets/cqs' directory for files matching the pattern
    'gXX_cqs.txt' or 'gXX_cqs.json', where XX is a two-digit number, and returns the next
    generation number in the format 'gXX_cqs'. If no such files are found,

    Returns:
        str: The next generation number in the format 'gXX_cqs'.
        int: The maximum generation number found.
    """
    max_gen = 0
    pattern = re.compile(r"g(\d+)(?:_cqs)?(?:_reformulated)?(?:\.txt|\.json)?$")

    for fname in os.listdir(os.path.join(os.getcwd(), "assets", "cqs")):
        matchname = pattern.search(fname)
        if matchname:
            gen_number = int(matchname.group(1))
            if gen_number > max_gen:
                max_gen = gen_number
    return f"g{max_gen + 1:02d}_cqs", max_gen
