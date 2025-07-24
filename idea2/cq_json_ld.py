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


def convert_cq_to_json_ld(cq: str, 
                          identifier=None, modelname=None, temperature="", roleset="", id=None, hash=None) -> dict:
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
        "text": cq
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
    

    json_ld_list = [convert_cq_to_json_ld(cq, identifier, modelname, temperature, roleset, hash=utils.hash_from_string(cq)) for cq in cqs]
    save_json_ld_to_file(json_ld_list, filepath)

    logging.info(f"Competency questions written to {filepath}")
    time.sleep(3)