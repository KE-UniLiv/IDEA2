"""

This script writes the competency questions (CQs) to a Notion database given that the CQs are
already cleaned and stored in a text file. It uses the Notion API to create new entries in the specified database for each CQ.

This script also facilitates multiple use cases, such as adding remote CQs from a dataset, setting up LLM configurations in Notion,
"""

import os
import pprint
import json
from utils import get_key, subset_cqs_from_dataset
from notion_client import Client
from tqdm import tqdm
from reformulate_cq import NOTION_DATABASE_ID, get_name_from_id, get_discussion_comments
from time import sleep

notiontoken = get_key("notionkey")
llmdb = get_key("notionllmdb")
notiondb = get_key("notiondb")

notion = Client(auth=notiontoken)


def get_current_iteration_from_dashboard() -> int:
    """
    
    Get the current iteration number from the Notion database (more robust than from the file generation number).

    Returns:
        int: The current iteration number.
    
    """
    all_results = []

    iteration_numbers = set()
    has_more = True
    next_cursor = None

    while has_more:
        response = notion.databases.query(
            **{
                "database_id": NOTION_DATABASE_ID,
                "filter": {
                    "property": "Iteration",
                    "number": {
                        "is_not_empty": True
                    }
                },
                "start_cursor": next_cursor
            }
        )
        all_results.extend(response["results"])
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")
    
    for page in all_results:
        if 'Iteration' in page['properties'] and page['properties']['Iteration']['number'] is not None:
            iteration_number = page['properties']['Iteration']['number']
            iteration_numbers.add(iteration_number)

    iteration_number = max(iteration_numbers) if iteration_numbers else 1
    print(f"Current iteration number is: {iteration_number}")
    return iteration_number
    
 
def write_row(client, database_id, string, cq, iteration, generation_config, src_documents) -> None:
    """
    Write a row to the Notion database with the given user_id and competency question (cq).

    Args:

        client: The Notion client instance.
        database_id: The ID of the Notion database where the row will be written.
        user_id: The user ID to associate with the row (not used in this example).
        cq: The competency question to write to the database.
        src_documents: The source documents associated with the CQ.

    
    This then creates a new row in the specified Notion database with the competency question to facilitate accept / reject.
    
    """

    client.pages.create(
        **{
            "parent": {
                "database_id": database_id
            },
            'properties': {
                'CQ': {'title': [{'text': {'content': cq}}]},
                'Source': {'multi_select': [{'name': src_documents}]},
                'Generation Config': {'relation': [{'id': generation_config}]},
                'Iteration': {'number': int(iteration)},
                # 'CQ': {'select': {'name': event}},
                # 'Date': {'date': {'start': date}}
            }
        }
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

def archive_all_pages(database_id):
    has_more = True
    next_cursor = None
    while has_more:
        response = notion.databases.query(
            **{
                "database_id": database_id,
                "page_size": 100,
                "start_cursor": next_cursor
            }
        )
        for page in tqdm(response["results"], desc="Archiving pages"):
            page_id = page["id"]
            notion.pages.update(page_id=page_id, archived=True)
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor", None)
    
    print("All pages have been archived.")

def link_reformulations():
    pass

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
    

def remote_add_cqs(filepath, n):
    cqs = subset_cqs_from_dataset(filepath, n)
    for cq in tqdm(cqs, desc="Adding remote CQs to Notion"):
        write_row(
            client=notion,
            database_id=notiondb,
            cq=cq,
            iteration=get_current_iteration_from_dashboard(),
            generation_config="",
            src_documents="bme"
        )


if __name__ == "__main__":
    remote_add_cqs(os.path.join(os.getcwd(), "assets", "us_personas", "askcq_dataset.csv"), 23)
