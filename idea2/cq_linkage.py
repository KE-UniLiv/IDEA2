"""

Module to link a reformulated CQ to its original CQ in Notion.

"""

from notion_client import Client
from utils import get_key, lookup_text_by_hash
from reformulate_cq import NOTION_DATABASE_ID


notiontoken = get_key("notionkey")
llmdb = get_key("notionllmdb")
notiondb = get_key("notiondb")

notion = Client(auth=notiontoken)

def find_original_cq_from_hash(rejected_cq_hash: str) -> str:
    return lookup_text_by_hash(rejected_cq_hash, "assets/cqs/hash_text_tuples.json")

def src_cq_uuid(rejected_cq_hash: str) -> str:
    title = lookup_text_by_hash(rejected_cq_hash, "assets/cqs/hash_text_tuples.json")

    if title is None:
        print(f"No original CQ found for hash: {rejected_cq_hash}")
        return None

    # Query Notion for a page with an exact match on the 'CQ' property
    has_more = True
    next_cursor = None

    while has_more:
        query_kwargs = {
            "database_id": notiondb,
            "filter": {
                "property": "CQ",
                "title": {
                    "equals": title
                }
            },
            "page_size": 100
        }
        if next_cursor:
            query_kwargs["start_cursor"] = next_cursor

        response = notion.databases.query(**query_kwargs)
        results = response.get("results", [])
        if results:
            # Return the first matching page's UUID
            return results[0]["id"]

        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor", None)

    print(f"No Notion page found with title: {title}")
    return None

def get_page_id_by_title(title: str, database_id=notiondb) -> str:
    has_more = True
    next_cursor = None

    while has_more:
        query_kwargs = {
            "database_id": database_id,
            "filter": {
                "property": "CQ",
                "title": {
                    "equals": title
                }
            },
            "page_size": 100
        }
        if next_cursor:
            query_kwargs["start_cursor"] = next_cursor

        response = notion.databases.query(**query_kwargs)
        results = response.get("results", [])
        if results:
            return results[0]["id"]

        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor", None)

    return None

def link_reformulations(page_a_id: str, page_b_id: str) -> None:
    """
    Link two reformulated CQs in Notion by updating their properties.

    Args:
        page_a_id (str): The ID of the first page (reformulated CQ).
        page_b_id (str): The ID of the second page (original CQ).

    Returns:
        None
    """
    if not page_b_id:
        print(f"No Notion page found with ID: {page_b_id}")
        return

    notion.pages.update(
        page_id=page_a_id,
        properties={
            "Reformulates": {
                "relation": [{"id": page_b_id}]
            }
        }
    )
