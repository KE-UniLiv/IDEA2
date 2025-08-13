"""

This script writes the competency questions (CQs) to a Notion database given that the CQs are
already cleaned and stored in a text file. It uses the Notion API to create new entries in the specified database for each CQ.

"""

import os
import json
import logging
import time
from utils import get_key
from notion_client import Client
from tqdm import tqdm

notiontoken = get_key("notionkey")
llmdb = get_key("notionllmdb")
notiondb = get_key("notiondb")

notion = Client(auth=notiontoken)

# BIG TODO: GET THE UUID OR ID OR WHATEVER IT IS FROM THE TEST CQ AND SEE IF LINKING IS FEASIBLE

def check_all_voted():
    """
    
    Ensures that all competency questions (CQs) have at least 1 vote.
    
    """

    results = notion.databases.query(
        **{
            "database_id": notiondb,
            "filter": { 
                "property": "Votes", 
                "number": {
                    "equals": 0
                }
            }
        }
    )

    if results["results"]:
        logging.warning("There are results with 0 votes. Waiting for 5 seconds before proceeding.")
        time.sleep(5)
    
 
def write_row(client, database_id, string, cq, iteration, generation_config, reformulates=None) -> None:
    """
    Write a row to the Notion database with the given user_id and competency question (cq).

    Args:

        client: The Notion client instance.
        database_id: The ID of the Notion database where the row will be written.
        user_id: The user ID to associate with the row (not used in this example).
        cq: The competency question to write to the database.

    
    This then creates a new row in the specified Notion database with the competency question to facilitate accept / reject.
    
    """

    properties = {
        'CQ': {'title': [{'text': {'content': cq}}]},
        'Source': {'multi_select': [{'name': 'AnIML (Core and Technique)'}]},
        'Generation Config': {'relation': [{'id': generation_config}]},
        'Iteration': {'number': int(iteration)}
    }

    if reformulates:
        properties['Reformulates'] = {'relation': [{'id': reformulates}]}
    client.pages.create(
        parent={'database_id': database_id},
        properties=properties
    )

def llm_setup_to_notion(generation, modelname, temperature, usage, prompt, llmrole, database_id=llmdb) -> None:
    """
    
    Add the LLM setup and its generated CQ reference to the Notion database.

    Args:
        generation (str): The generation ID for the LLM setup.
        modelname (str): The name of the model used.
        temperature (float): The temperature setting for the LLM.
        usage (str): The usage context for the LLM.
        prompt (str): The prompt text for the LLM.
        llmrole (str): The role of the LLM in the context.
        database_id (str): The ID of the Notion database where the LLM setup will be stored.

    Returns:
        None: The function creates a new page in the Notion database with the LLM setup information.
    
    """
    
    page = notion.pages.create(
        **{
            "parent": {
                "database_id": database_id,
            },
            'properties': {
                'ID': {'title': [{'text': {'content': generation}}]},
                'Model': {'select': {'name': modelname}},
                'Temperature': {'number': temperature},
                'Usage': {'select': {'name': usage}},
                'Role': {'rich_text': [{'text': {'content': llmrole}}]},
                'Prompt': {'rich_text': [{'text': {'content': prompt}}]}
            }
        }
    )
    return page["id"]

def get_ids():

    results = notion.databases.query(
        **{
            "database_id": notiondb,
            "filter": {
                "property": "ID",
                "unique_id": {
                    "is_not_empty": True
                }
            }
        }
    )

    # Return list of dicts: {"id": page id, "title": CQ title}
    return [
        {
            "id": page["id"],
            "title": page["properties"]["CQ"]["title"][0]["text"]["content"] if "CQ" in page["properties"] and page["properties"]["CQ"]["title"] else None
        }
        for page in results["results"]
    ]

def get_notion_id_for_cq(cq: str, entries=get_ids()) -> str:
    """
    Get the Notion page ID for a specific competency question (CQ).

    Args:
        cq (str): The competency question to search for.
        entries (list): A list of entries containing CQ titles and their corresponding Notion page IDs.

    Returns:
        str: The Notion page ID associated with the given CQ, or None if not found.
    """
    for entry in entries:
        if entry["title"] == cq:
            return entry["id"]
    return None

def get_cqs_from_file(filepath, filetype=None) -> list:
    """
    Read competency questions from a file and return them as a list.

    Args:
        filepath: The path to the file containing competency questions.
        filetype: The type of the file (optional). If 'txt', it reads from a text file; if 'json' or 'jsonld', it reads from a JSON file.

    Returns:
        A list of competency questions.
    
    Note that the CQs should already be cleaned.
    
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"The file {filepath} does not exist.")
    
    if filetype and filetype.lower() not in ['txt', 'json', 'jsonld']:
        raise ValueError("Unsupported file type. Please use 'txt', 'json' or 'jsonld'.")
    
    if filetype and filetype.lower() == 'txt':
        with open(filepath, 'r') as file:
            cqs = file.readlines()

        return [cq.strip() for cq in cqs if cq.strip()]

    else:
        with open(filepath, 'r') as file:
            cqs = json.load(file)
        
        cq_strings = [item["text"] for item in cqs if "text" in item]

        print(cq_strings)
        return [cq.strip() for cq in cq_strings if cq.strip()]
    

def getn(database_id=notiondb) -> int:
    """
    Get the number of unique voters (participants) from the Notion database.

    Args:
        database_id (str): The ID of the Notion database to query.

    Returns:
        int: The number of unique participants who voted on any CQ.
    """

    unique_voters = set()
    has_more = True
    next_cursor = None

    while has_more:
        query_kwargs = {
            "database_id": database_id,
            "page_size": 100,
        }

        if next_cursor:
            query_kwargs["start_cursor"] = next_cursor

        results = notion.databases.query(**query_kwargs)
        
        for page in results["results"]:
            for prop in ["Upvoted By", "Downvoted By"]:
                if prop in page["properties"]:
                    people = page["properties"][prop].get("people", [])
                    for person in people:
                        unique_voters.add(person["id"])
        has_more = results.get("has_more", False)
        next_cursor = results.get("next_cursor", None)

    return len(unique_voters)

if __name__ == "__main__":
    # Get the database properties for debugging
    db = notion.databases.retrieve(database_id=notiondb)
    print(db['properties'].keys())