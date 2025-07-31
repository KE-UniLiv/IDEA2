"""

Use pydantic to define the output constraints for the competency question extraction process.

"""


from pydantic import BaseModel, Field, RootModel
from typing import List, Optional

import json

class CompetencyQuestion(RootModel[List[str]]):
    """
    Represents a competency question with its text 
    """
    pass


def validate_competency_questions(llm_output) -> List[str]:
    """
    Validates the output from the LLM to ensure it conforms to the expected format of a list of competency questions.

    Args:
        llm_output (str): The output from the LLM, expected to be a JSON string representing a list of competency questions.
    Returns:
        List[str]: A list of competency questions if the output is valid.

    Raises:
        ValueError: If the output is not a valid JSON string or does not conform to the expected format.
    """

    try:
        validated = CompetencyQuestion.model_validate(llm_output)
        return validated.__root__
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")
    

    
