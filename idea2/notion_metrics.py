from notion_client import Client
from utils import get_key

notiondb = None
notiontoken = None
notion = None

def _ensure_config():
    """Lazy initialization of Notion configuration."""
    global notiondb, notiontoken, notion
    if notiondb is None:
        notiondb = get_key("notiondb")
        notiontoken = get_key("notionkey")
        notion = Client(auth=notiontoken)

def getn(database_id=None) -> int:
    _ensure_config()
    if database_id is None:
        database_id = notiondb
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

def dump_metrics_to_file(data, filetype):
    pass