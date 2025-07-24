"""

This script pulls accepted and rejected competency questions (CQs) from a Notion database and allows for their reformulation using a large language model (LLM).

"""



import logging
import time
import os
import json
import datetime
import prompts as p
import cq_measures
import sys

from notion_client import Client
from utils import get_key
from tqdm import tqdm 
from generation_utils import get_generation_number

geminikey = get_key("gemini")
openai_key = get_key("openai")

LLMDB = get_key("notionllmdb") # This should be your Notion database ID for LLM setups
NOTION_TOKEN = get_key("notionkey") # This should be your Notion integration token
NOTION_PAGE_ID = get_key("notionpage")  # This should be your Notion page ID
NOTION_DATABASE_ID = get_key("notiondb")  # This should be your Notion database ID

notion = Client(auth=NOTION_TOKEN)
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # Suppress httpx warnings

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
            person = get_name_from_id(people[0]["id"]) if people else "Unknown"

            accepted_cqs.append({"title": title})

    return accepted_cqs

def pull_rejected() -> dict:
    """
    Pulls rejected competency questions from the Notion database.

    Returns:
        dict: A dict of rejected competency questions, their rejector, and any comments.
    """

    logging.info("Pulling rejected competency questions from Notion database.")
    _, curriteration = get_generation_number()
    
    ## -- Query the Notion database for rejected CQs
    results = notion.databases.query(
        **{
            "database_id": NOTION_DATABASE_ID,
            "filter": { 
                "property": "Score", 
                "number": {
                    "less_than": 0 
                }
            }
        }
    )
    
    
    rejected_cqs = []
    count = 0

    for page in results['results']:
        if 'CQ' in page['properties'] and page['properties']['CQ']['title']:
            idx = page["properties"]["ID"]["unique_id"]["number"]

            title = page["properties"]["CQ"]["title"][0]["text"]["content"]
            people = page["properties"]["Downvoted By"]["people"]
            score = page["properties"]["Score"]["formula"]["number"]
            votes = page["properties"]["Votes"]["formula"]["number"]
            iteration = page["properties"]["Iteration"]["number"]

            person = ", ".join(get_name_from_id(person["id"]) for person in people) if people else "Unknown user"
            comments = get_discussion_comments(page['id'])

            if comments:
                comment = "".join(f"<comment> {c} </comment>" for c in comments)
            else:
                comment = "<comment>No comment given. Check this CQ with the schema and generalise to the requirement.</comment>"
            
            readabledate = datetime.datetime.strptime(page["properties"]["Creation date"]["created_time"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y")
            rejected_cqs.append({
                "title": title,
                "id": idx,
                "person": person,
                "creation date": readabledate,
                "score": score,
                "votes": votes,
                "comment": comment,
                "from iteration": iteration,
                "date_pulled": datetime.datetime.now().strftime("%d/%m/%y")
            })

    if curriteration == 1:
        filtered_cqs = rejected_cqs
        print("No previous iterations to filter. Using all rejected CQs.")
    else:
        prev_iteration = curriteration - 1
        filtered_cqs = [cq for cq in rejected_cqs if cq["from iteration"] == prev_iteration]

        count = len(rejected_cqs) - len(filtered_cqs)
        print(f"Removed {count} CQs that were not from the previous iteration.")

        if len(filtered_cqs) == 0:
            print("No new rejected CQs found, exiting to avoid overwriting!")
            sys.exit(0)

    return filtered_cqs

def get_ids_from_rejected(rejected_cqs: list) -> list:
    """
    Extracts the IDs of rejected competency questions.

    Args:
        rejected_cqs (list): A list of rejected competency questions.

    Returns:
        list: A list of IDs of the rejected competency questions.
    
    """
    
    return [cq["id"] for cq in rejected_cqs if "id" in cq]

def get_name_from_id(user_id: str) -> str:
    """
    Retrieves the name of a user from their ID.

    Args:
        user_id (str): The ID of the user.

    Returns:
        str: The name of the user, or "Unknown" if not found.

    """
    try:
        user = notion.users.retrieve(user_id)
        return user.get("name", "Unknown")
    except Exception as e:
        logging.warning(f"Error retrieving user {user_id}: {e}")
        return "Unknown user"


def store_pulled(pulled_cqs, typeof="none") -> None:
    """
    Stores rejected competency questions in a JSON file.

    Args:
        pulled_cqs (list): A list of pulled competency questions.
        typeof (str): The type of competency questions being stored (e.g., "accepted", "rejected").

    Returns:
        None: The function saves the pulled competency questions to the specified file.

    """

    filepath = os.path.join(os.getcwd(), "assets", "cqs", f"{typeof}_cqs.json")
    with open(filepath, 'w') as f:
        json.dump(pulled_cqs, f, indent=2, ensure_ascii=False)

def store_handled(handled_path: str, rejected_path: str) -> None:
    """
    Stores handled competency questions in a JSON file.

    Args:
        handled_path (str): The path to the handled CQs JSON file.
        rejected_path (str): The path to the rejected CQs JSON file.

    Returns:
        None: The function saves the handled competency questions to the specified file.

    """

    # Load existing handled CQs if file exists
    if os.path.exists(handled_path):
        with open(handled_path, 'r', encoding='utf-8') as f:
            try:
                handled_cqs = json.load(f)
            except Exception:
                handled_cqs = []
    else:
        handled_cqs = []

    # Load new handled CQs
    with open(rejected_path, 'r', encoding='utf-8') as f:
        try:
            new_cqs = json.load(f)
        except Exception:
            new_cqs = []

    ## -- Only append CQs whose IDs are not already in handled_cqs
    existing_ids = set(cq.get("id") for cq in handled_cqs if isinstance(cq, dict) and cq.get("id") is not None)
    to_add = [cq for cq in new_cqs if isinstance(cq, dict) and cq.get("id") not in existing_ids]
    all_handled = handled_cqs + to_add

    print(f"to_add: {to_add}")

    with open(handled_path, 'w', encoding='utf-8') as f:
        json.dump(all_handled, f, indent=2, ensure_ascii=False)
    
def get_discussion_comments(page_id: str) -> list:
    """
    Retrieves discussion comments attached to a Notion page (i.e. database item).

    Args:
        page_id (str): The Notion page ID (i.e. the database row).

    Returns:
        list: A list of comment strings.

    """
    try:
        comments = notion.comments.list(block_id=page_id)
        return [c['rich_text'][0]['text']['content'] for c in comments['results'] if c['rich_text']]
    except Exception as e:
        logging.warning(f"Could not fetch comments for page {page_id}: {e}")
        return []



    
def get_rejected_cqs_from_file() -> list:
    """
    Reads rejected competency questions from a file and returns them as a list.

    Returns:
        list: A list of rejected competency questions.

    Note:
        The CQs should already be cleaned and stored in 'assets/cqs/rejected_cqs.json'.
    """

    filepath = os.path.join(os.getcwd(), "assets", "cqs", "rejected_cqs.json")
    _, iteration = get_generation_number()


    with open(filepath, 'r', encoding='latin-1') as f:
        try:
            data = json.load(f)
        except Exception as e:
            return []
            

    cqs = [{
        "cq": item["title"],
        "id": item.get("id", ""),
        "comment": item.get("comment", "No comment provided"),
        "score": item.get("score", {}).get("formula", {}).get("number", 0) if isinstance(item.get("score"), dict) else item.get("score", 0),
        "votes": item.get("votes", {}).get("formula", {}).get("number", 0) if isinstance(item.get("votes"), dict) else item.get("votes", 0),
        "from iteration": iteration,

    } for item in data if 'title' in item and 'id' in item and 'comment' in item and 'score' in item and 'votes' in item]

    return cqs

def get_cqs_from_file_as_strings(filepath) -> list:
    """
    Reads rejected competency questions from a file and returns them as a list of formatted strings.

    Args:
        filepath (str): The path to the file containing rejected competency questions.

    Returns:
        list: A list of rejected competency questions as formatted strings.

    Note:
        The CQs should already be cleaned and stored in 'assets/cqs/rejected_cqs.json'.
    """

    with open(filepath, 'r', encoding='latin-1') as f:
        data = json.load(f)

    cqs = []
    for item in data:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "")
        comment = item.get("comment", "")
        score = item.get("score", {}).get("formula", {}).get("number", "") if isinstance(item.get("score"), dict) else item.get("score", "")
        votes = item.get("votes", {}).get("formula", {}).get("number", "") if isinstance(item.get("votes"), dict) else item.get("votes", "")
        cqs.append(f"{title} was rejected with {comment}, {votes} votes and {score} score")

    return cqs

def reformulate_cqs(model: object, prompt: str, cqs: list) -> list:
    """
    Reformulates competency questions using the LLM.

    Args:
        model (object): The LLM instance to use for reformulation.
        prompt (str): The initial prompt to guide the LLM in reformulating the competency questions.
        cqs (list): A list of competency questions to be reformulated.

    Returns:
        list: A list of reformulated competency questions.
    
    """

    ## -- Serialize the list of CQs as JSON and append to the prompt for structured input
    prompt = prompt + "\nHere are the rejected competency questions as structured data (JSON):\n\n"

    try:
        cqs_json = json.dumps(cqs, indent=2, ensure_ascii=False)
        prompt = prompt + cqs_json + "\n"

    except Exception as e:
        logging.error(f"Error while serializing CQs to JSON: {e}")
        return []
    
    return model.generate(prompt=prompt)


def validate_reformulated(cqs: list, count: int = 0) -> list:
    """
    Validates the reformulated competency questions using output constraints.

    Args:
        cqs (list): A list of reformulated competency questions directly from the LLM output.

    Returns:
        list: A list of validated competency questions, excluding any that do not meet the output constraints.
        
    """

    cqs = [cq for cq in cqs if "N/A" not in cq]
    return cqs if cqs else ["No competency questions were needed to be validated."]
