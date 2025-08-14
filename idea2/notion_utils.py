"""

This script writes the competency questions (CQs) to a Notion database given that the CQs are
already cleaned and stored in a text file. It uses the Notion API to create new entries in the specified database for each CQ.

"""

import os
import pprint
import json
from utils import get_key
from notion_client import Client
from tqdm import tqdm
from reformulate_cq import NOTION_DATABASE_ID, get_name_from_id, get_discussion_comments
from time import sleep

notiontoken = get_key("notionkey")
llmdb = get_key("notionllmdb")
notiondb = get_key("notiondb")

notion = Client(auth=notiontoken)

# BIG TODO: GET THE UUID OR ID OR WHATEVER IT IS FROM THE TEST CQ AND SEE IF LINKING IS FEASIBLE

def test_relation(client, database_id):

    results = notion.databases.query(
        **{
            "database_id": notiondb,
            "filter": { 
                "property": "ID", 
                "number": {
                    "equals": 1618
                }
            }
        }
    )

    for page in results["results"]:
        reformulates = page["properties"].get("Reformulates")
        print(reformulates)
        
def get_all_cqs():
    all_results = []
    has_more = True
    next_cursor = None

    while has_more:
        response = notion.databases.query(
            **{
                "database_id": NOTION_DATABASE_ID,
                "filter": {
                    "property": "CQ",
                    "title": {
                        "is_not_empty": True
                    }
                },
                "start_cursor": next_cursor
            }
        )
        all_results.extend(response["results"])
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")

    return len(all_results)

def pull_all_comments_and_comments():
    pass


def get_metrics_by_iteration(iteration:int = 1) -> str:

    print("Loading Iteration Metrics...")
    accepted_cqs = pull_accepted()

    unique = set(c["title"] for c in accepted_cqs if c["iteration"] == iteration)
    number_of_accepted = len(unique)

    all_results = []
    has_more = True
    next_cursor = None

    while has_more:

        response = notion.databases.query(
            **{
                "database_id": NOTION_DATABASE_ID,
                "filter": {
                    "property": "Iteration",
                    "number": {
                        "equals": iteration
                    }
                },
                "start_cursor": next_cursor
            }
        )
        all_results.extend(response["results"])
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")



    total_cqs_in_iter = len(all_results)
    percent = (number_of_accepted / total_cqs_in_iter * 100) if total_cqs_in_iter > 0 else 0

    os.system("CLS")
    report = f"Iteration {iteration}: {number_of_accepted} CQs had at least 1 or more acceptance in total ({percent:.2f}%)"

    print(report)
    sleep(2)
    print(f"\nThere was a total of {total_cqs_in_iter} CQs")
    sleep(2)
    print(f"This leaves {total_cqs_in_iter - number_of_accepted} CQs that were unanimously rejected by all participants")

    return report


def pull_accepted() -> dict:
    """
    Pulls accepted competency questions from the Notion database.

    Returns:
        dict: A dict of accepted competency questions.
    """
    
    ## -- Query the Notion database for accepted CQs
    results = notion.databases.query(
        **{
            "database_id": NOTION_DATABASE_ID,
            "filter": {
                "property": "Upvoted By",
                "people": {
                    "is_not_empty": True  # TODO: Change this to domain experts user IDs
                }
            }
        }
    )
    
    ## -- Extract titles of accepted CQs
    accepted_cqs = []

    for page in results['results']:
        if 'CQ' in page['properties'] and page['properties']['CQ']['title']:
            title = page["properties"]["CQ"]["title"][0]["text"]["content"]
            people = page["properties"]["Upvoted By"]["people"]
            iteration = page["properties"]["Iteration"]["number"]

            for person_obj in people:
                person_id = person_obj["id"]
                accepted_cqs.append({"title": title, "person": person_id, "iteration": iteration})

    return accepted_cqs

def pull_comments():
    """
    Pulls comments from the Notion database along with their authors and associated CQ titles.
    Returns comment counts per unique person.
    """

    os.system("CLS")
    print("Processing comments...\n\n")
    comments = []
    has_more = True
    next_cursor = None

    while has_more:
        response = notion.databases.query(
            **{
                "database_id": NOTION_DATABASE_ID,
                "filter": { 
                    "property": "Score", 
                    "number": {
                        "less_than_or_equal_to": 0 
                    }
                },
                "start_cursor": next_cursor
            }
        )
        
        for page in response["results"]:
            # Extract CQ title
            title = None
            if 'CQ' in page['properties'] and page['properties']['CQ']['title']:
                title = page["properties"]["CQ"]["title"][0]["text"]["content"]
                comment_text = get_discussion_comments(page["id"])
                people = page["properties"]["Downvoted By"]["people"]
                
                # Add one comment entry per person who downvoted
                for person in people:
                    person_name = get_name_from_id(person["id"])
                    comments.append({
                        "title": title,
                        "comment": comment_text,
                        "author": person_name,
                        "author_id": person["id"]
                    })
        
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")

    # Count comments per unique person
    comment_counts = {}
    for comment in comments:
        author = comment["author"]
        if author not in comment_counts:
            comment_counts[author] = {
                "count": 0,
                "comments": []
            }
        comment_counts[author]["count"] += 1
        comment_counts[author]["comments"].append({
            "title": comment["title"],
            "comment": comment["comment"]
        })

    print(f"Total comments pulled: {len(comments)}")
    print(f"\nComment counts per annotator:")
    
    for author, data in comment_counts.items():
        print(f"{author}: {data['count']} comments")
        # Optionally print their actual comments:
        # for i, comment in enumerate(data['comments'], 1):
        #     print(f"  {i}. CQ: {comment['title']}")
        #     print(f"     Comment: {comment['comment'][:100]}...")

    return comments, comment_counts

def get_negative_cq_metrics(iteration: int = 1):
    all_results = []
    has_more = True
    next_cursor = None
    reject_list = []  # Changed from dict to list

    while has_more:
        response = notion.databases.query(
            **{
                "database_id": NOTION_DATABASE_ID,
                "filter": {
                    "property": "Score",
                    "number": {
                        "less_than_or_equal_to": 0
                    }
                },
                "start_cursor": next_cursor
            }
        )
        all_results.extend(response["results"])
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")

    for page in all_results:
        # Extract CQ title
        if 'CQ' in page['properties'] and page['properties']['CQ']['title']:
            # Check if page has iteration property and matches the target iteration
            if (page['properties'].get('Iteration') and 
                page['properties']['Iteration'].get('number') == iteration):
                
                title = page["properties"]["CQ"]["title"][0]["text"]["content"]
                
                # Handle both formula and direct number types
                score_prop = page["properties"]["Score"]
                if score_prop.get("formula"):
                    score = score_prop["formula"]["number"]
                else:
                    score = score_prop.get("number", 0)
                
                # Append to list instead of updating dict
                reject_list.append({"CQ": title, "Score": score})

    total_rejected_in_iter = len(reject_list)

    print(f"Total rejected CQs in iteration {iteration}: {total_rejected_in_iter}")
    
    # Pretty print the rejected CQs
    print("Rejected CQs:")
    pprint.pprint(reject_list, indent=2, width=100)
    
    return reject_list

def get_cq_metrics_by_user():
    print("Loading CQ Metrics by User...")
    accepted_cqs = pull_accepted()
    number_of_cqs = get_all_cqs()

    annotators = list({cq["person"] for cq in accepted_cqs})
    for idx, annotator in enumerate(annotators):
        number_of_accepted = sum(1 for c in accepted_cqs if c["person"] == annotator)
        percent = (number_of_accepted / number_of_cqs * 100) if number_of_cqs > 0 else 0

        print(f"Annotator {idx+1} has accepted {number_of_accepted} out of {number_of_cqs} CQs ({percent:.2f}%)")
        sleep(2)
    print("==="*45)
    print("\n")

def get_comment_metrics_by_user():
    print("Loading CQ Metrics by User...")
    accepted_cqs = pull_accepted()
    number_of_cqs = get_all_cqs()

    annotators = list({cq["person"] for cq in accepted_cqs})
    for idx, annotator in enumerate(annotators):
        number_of_accepted = sum(1 for c in accepted_cqs if c["person"] == annotator)
        percent = (number_of_accepted / number_of_cqs * 100) if number_of_cqs > 0 else 0

        print(f"Annotator {idx+1} has accepted {number_of_accepted} out of {number_of_cqs} CQs ({percent:.2f}%)")
        sleep(2)
    print("==="*45)
    print("\n")


def write_row(client, database_id, string, cq, iteration, generation_config) -> None:
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
    

