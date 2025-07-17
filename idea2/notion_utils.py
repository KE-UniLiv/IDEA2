"""

This script writes the competency questions (CQs) to a Notion database given that the CQs are
already cleaned and stored in a text file. It uses the Notion API to create new entries in the specified database for each CQ.

"""

import os
import json
from utils import get_key
from notion_client import Client
from tqdm import tqdm
import uuid

# BIG TODO: GET IDENTIFIER OF A CQ FROM THE PRIMARY KEY IN THE NOTION DATABASE

notiontoken = get_key("notionkey")
llmdb = get_key("notionllmdb")

notion = Client(auth=notiontoken)
 
def write_row(client, database_id, user_id, cq, generation_config) -> None:
    """
    Write a row to the Notion database with the given user_id and competency question (cq).

    Args:

        client: The Notion client instance.
        database_id: The ID of the Notion database where the row will be written.
        user_id: The user ID to associate with the row (not used in this example).
        cq: The competency question to write to the database.

    
    This then creates a new row in the specified Notion database with the competency question to facilitate accept / reject.
    
    """

    client.pages.create(
        **{
            "parent": {
                "database_id": database_id
            },
            'properties': {
                'CQ': {'title': [{'text': {'content': cq}}]},
                'Source': {'multi_select': [{'name': 'AnIML (Core and Technique)'}]},
                'Generation Config': {'relation': [{'id': generation_config}]},
                # 'CQ': {'select': {'name': event}},
                # 'Date': {'date': {'start': date}}
            }
        }
    )

def llm_setup_to_notion(generation, modelname, temperature, usage, prompt, llmrole, database_id=llmdb) -> None:
    """
    
    Add the LLM setup and its generated CQ reference to the Notion database.

    Args:
        database_id (str): The ID of the Notion database where the LLM setup will

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

def get_cqs_from_file(filepath, filetype=None) -> list:
    """
    Read competency questions from a file and return them as a list.

    Args:
        filepath: The path to the file containing competency questions.

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
