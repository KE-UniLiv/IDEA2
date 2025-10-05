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
from notion_utils import get_current_iteration_from_dashboard
#from pyld import jsonld ## -- Useful in case we need to do any JSON-LD processing / operations later, but not intrinsically needed for the conversion


def convert_cq_to_json_ld(cq: str, 
                          generation_identifier=None, modelname=None, temperature="", roleset="", id=None, hash=None, src_cq=None) -> dict:
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
        "@Generation": generation_identifier if generation_identifier else "",
        "@URI": hash if hash else "",
        "@Reformulates": src_cq if src_cq else "None",
        "text": cq
    }

    json_ld["identifier"] = generation_identifier if generation_identifier else "undefined"

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

    generation_identifier, _ = get_generation_number()
    modelname = cq_extraction.config["gemini_model"]
    temperature = cq_extraction.config["temperature"]
    roleset = cq_extraction.config["role"]

    curr_iteration = get_current_iteration_from_dashboard()

    if curr_iteration == 1:
        src_cq = None
    else:
        raise NotImplementedError("Reformulated CQs not yet implemented in JSON-LD conversion.")

    json_ld_list = [convert_cq_to_json_ld(cq, generation_identifier, modelname, temperature, roleset, hash=utils.hash_from_string(cq), src_cq=src_cq) for cq in cqs]
    save_json_ld_to_file(json_ld_list, filepath)

    logging.info(f"Competency questions written to {filepath}")
    time.sleep(3)