"""This module constrains the output of the LLM, especially for the enrichment of Ontologies with Competency Questions (CQs)."""


from pydantic import BaseModel, Field

class CompetencyQuestion(BaseModel):
    """
    
    Defines a simple pydantic model for structuring output for CQs, especially for enrichment of CQs

    Attributes:
        question (str): The competency question text.
        classes (list[str]): The classes associated with the competency question from the ontology.
        relationships (list[str]): The relationships associated with the competency question from the ontology.

    """
    question: str 
    classes: list[str] 
    relationships: list[str] 



