"""

Script to facilitate the conversion of competency questions (CQs) to JSON-LD format.

"""


import json
import os
import logging
import time
import cq_extraction
import utils
from generation_utils import get_generation_number
from pyld import jsonld ## -- Useful in case we need to do any JSON-LD processing / operations later, but not intrinsically needed for the conversion
from output_constraints import CompetencyQuestion
from tqdm import tqdm

def convert_cq_to_json_ld(cq: str, 
                          identifier=None, modelname=None, temperature="", roleset="", 
                          id=None, hash=None, classes="", relationships="") -> dict:
    """
    Convert a competency question (CQ) to JSON-LD format.

    Args:
        cq (str): The competency question to convert.
        identifier (str, optional): An identifier for the competency question. Defaults to None.
        set (str, optional): The name of the set to which the competency question belongs.

    Returns:
        dict: The JSON-LD representation of the competency question.
    """
    
    json_ld = {
        "@context": "https://www.animl.org/",
        "@type": "CompetencyQuestion",
        "@ID": id if id else "",
        "@URI": hash if hash else "",
        "question": cq,
        "Class(es)": classes,
        "Relationship(s)": relationships

    }

    json_ld["identifier"] = identifier if identifier else "undefined"

    json_ld["belongsToModel"] = {"@type": "System", "name": modelname, "temperature": temperature, "roleset": roleset}  \
    if modelname else {"@type": "Collection", "name": "undefined"}

    return json_ld


def save_json_ld_to_file(json_ld_list: dict, filepath=None) -> None:
    """
    Save the JSON-LD representation to a file.

    Args:
        json_ld (dict): The JSON-LD representation of the competency question as a list, to store into one JSON.
        filepath (str): The path to the file where the JSON-LD will be saved.

    """

    filepath = os.path.join(os.getcwd(), "assets", "cqs", "all_questions.jsonld") if filepath is None else filepath

    with open(filepath, 'w') as f:
        json.dump(json_ld_list, f, indent=2, ensure_ascii=False)

def cq_to_json_ld(cqs: list, filepath=None) -> None:
    """
    Convert a list of competency questions to JSON-LD format and save them to a file.

    Args:
        cqs (list): A list of competency questions.
        filepath (str, optional): The path to the file where the JSON-LD will be saved. Defaults to None.

    Returns:
        None: The function saves the JSON-LD representation to the specified file.
    """

    identifier, _ = get_generation_number()
    modelname = cq_extraction.config["gemini_model"]
    temperature = cq_extraction.config["temperature"]
    roleset = cq_extraction.config["role"]
    
    if isinstance(cqs, CompetencyQuestion):
        cqs = [cqs]

    json_ld_list = []
    for cq in tqdm(cqs):
        ## -- If cq is a CompetencyQuestion object, use cq.question for hashing and get all relevant variables from schema fields
        if isinstance(cq, CompetencyQuestion):
            hash_val = utils.hash_from_string(cq.question)
            text_val = cq.question
            identifier = "Enrichment CQs"
        else:
            hash_val = utils.hash_from_string(str(cq))
            text_val = cq
        json_ld_list.append(
            convert_cq_to_json_ld(
                text_val, identifier, modelname, temperature, roleset, hash=hash_val, 
                classes=cq.classes, relationships=cq.relationships
            )
        )

    save_json_ld_to_file(json_ld_list, filepath)
    print("---"*20)
    logging.info(f"Competency questions written to {filepath}")
    time.sleep(3)