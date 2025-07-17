"""
This provides generalised prompt building functionalities to automatically
extract competency questions from schema definitions and examples.
"""

import prompts as p


class PromptBuilder:
    """
    This class provides a prompt builder for the language model. It is used 
    to generate prompts following an overall template, where each component
    may be included in the final prompt, and whose specific formulation is
    modularised. Templates are expected to be in the following form.
    ---------------------------------------------------------------------------
    - LLM role: SYSTEM_ROLE_A | SYSTEM_ROLE_B | none
    - CQ definition: CQ_DEFINITION_A | CQ_DEFINITION_B | none
    - CQ examples: CQ_EXAMPLES_A | CQ_EXAMPLES_B | CQ_EXAMPLES_C | none
    - CQ ext instructions: CQ_EXTRACTION_A | CQ_EXTRACTION_B | CQ_EXTRACTION_C
    - Raw data (AnIML schema definition, examples, etc.)
    ----------------------------------------------------------------------------
    A function `get_prompt(raw_data)` is then used to generate the final
    prompt by replacing the placeholder with the raw data.
    """

    def __init__(self,
                 role: str = p.OENG_ROLE,
                 out_definition: str = None,
                 out_examples: str = None,
                 out_instruction: str = p.CQ_INSTRUCTION_A,
                 limit: str = "Do not generate more than 150 Competency Questions."
                 ):
        """
        Initialise the prompt builder with the main components of the template.

        Parameters
        ----------
        role : str
            The role of the language model.
        out_definition : str
            A definition of competency questions.
        out_examples : str
            The examples of the competency questions.
        out_instruction : str
            The extraction instructions for the competency questions.
        """
        self.role = role
        self.out_definition = out_definition
        self.out_examples = out_examples
        self.out_instruction = out_instruction
        self.limit = limit

    def get_prompt(self, raw_data, include_role=False):
        """
        Generate the prompt by replacing the placeholders with the raw data.
        
        Parameters
        ----------
        raw_data : dict
            The raw data to be included in the prompt.
        """
        prompt = ""
        if self.role is not None and include_role:
            prompt += self.role + "\n\n"
        if self.out_definition is not None:
            prompt += self.out_definition + "\n\n"
        if self.out_examples is not None:
            prompt += self.out_examples + "\n\n"
        if self.out_instruction is not None:
            prompt += self.out_instruction + "\n\n"
        if self.limit is not None:
            prompt += self.limit + "\n\n"
            
        prompt += raw_data
        return prompt
