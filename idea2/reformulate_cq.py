"""

This script pulls accepted and rejected competency questions (CQs) from a Notion database and allows for their reformulation using a large language model (LLM).

"""



import logging
import time
import os
import json
import datetime
import prompts as p

from notion_client import Client
from utils import get_key
from tqdm import tqdm 

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
    logging.info("Pulling accepted competency questions from Notion database.")
    
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

            accepted_cqs.append({"title": title, "person": person})

    return accepted_cqs

def pull_rejected() -> dict:
    """
    Pulls rejected competency questions from the Notion database.

    Returns:
        dict: A dict of rejected competency questions, their rejector, and any comments.
    """

    logging.info("Pulling rejected competency questions from Notion database.")
    
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
    
    ## -- Extract titles of rejected CQs
    rejected_cqs = []

    for page in results['results']:

        if 'CQ' in page['properties'] and page['properties']['CQ']['title']:
            title = page["properties"]["CQ"]["title"][0]["text"]["content"]
            people = page["properties"]["Downvoted By"]["people"]

            person = get_name_from_id(people[0]["id"]) if people else "Unknown user"

            comments = get_discussion_comments(page['id'])
            comment = comments[0] if comments else "No comment given. Check this CQ with the schema and generalise to the requirement."
            
            readabledate = datetime.datetime.strptime(page["properties"]["Creation date"]["created_time"], "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y")

            rejected_cqs.append({
                "title": title,
                "person": person,
                "creation date": readabledate,
                "score": page["properties"]["Score"],
                "comment": comment,
                "date_pulled": datetime.datetime.now().strftime("%d/%m/%y") ## -- Add the date of rejection
            })

    return rejected_cqs

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

    """

    filepath = os.path.join(os.getcwd(), "assets", "cqs", f"{typeof}_cqs.json")
    with open(filepath, 'w') as f:
        json.dump(pulled_cqs, f, indent=2, ensure_ascii=False)
    
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

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cqs = []
    for item in data:
        if 'title' in item and 'comment' in item:
            cqs.append(f"{item['title']} was rejected because {item['comment']}")
        else:
            cqs.append(item['title'])

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

    ## -- Iterate over the list of CQs and append each one to the end of the prompt

    prompt = prompt + "\nHere are the rejected competency questions:\n\n"

    try:
        for cq in cqs:
            cq = cq.strip()
            prompt = prompt + cq + "\n"
    except Exception as e:
        logging.error(f"Error while appending CQs to prompt: {e}")
        return []
    print(f"Prompt for reformulation:\n{prompt}\n")

    
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


   
if __name__ == "__main__":

    os.system("CLS")
    accepted_cqs = pull_accepted()
    
    for cq in accepted_cqs:
        print(f"Accepted CQ {cq['title']} accepted by {cq['person']}")

    time.sleep(5)
    print("----------------------------------------------------------------------------------")

    rejected_cqs = pull_rejected()
    if rejected_cqs:

        logging.info(f"Found {len(rejected_cqs)} rejected competency questions.")
        for cq in rejected_cqs:
            print(f"Rejected CQ {cq['title']} rejected by {cq['person']} with comment: {cq['comment']}")

    else:
        logging.info("No rejected competency questions found.")

    time.sleep(5)
    print("----------------------------------------------------------------------------------")

