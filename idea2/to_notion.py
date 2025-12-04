from notion_client import Client
from tqdm import tqdm
from time import sleep
import os
from utils import get_key
from pathlib import Path
import re
import pandas as pd

notiontoken = get_key("notionkey")
llmdb = get_key("notionllmdb")
notiondb = get_key("notiondb")

notion = Client(auth=notiontoken)


def read_cqs(filepath: str = os.path.join(os.getcwd(), "assets", "cqs", "extracted_original_cqs_with_comments.txt")) -> None:
    content = Path(filepath).read_text(encoding='utf-8')
    
    # Split by double newlines to separate entries
    entries = content.strip().split('\n\n')
    
    cq_list = []
    
    for entry in entries:
        if not entry.strip():
            continue
            
        lines = entry.strip().split('\n')
        
        cq_data = {
            'id': '',
            'original_cq': '',
            'comment': '',
            'reformulation': ''
        }
        
        for line in lines:
            if line.startswith('ID:'):
                cq_data['id'] = line.replace('ID:', '').strip()
            elif line.startswith('Original CQ:'):
                cq_data['original_cq'] = line.replace('Original CQ:', '').strip()
            elif line.startswith('Comment:'):
                cq_data['comment'] = line.replace('Comment:', '').strip()
            elif line.startswith('Reformulation:'):
                cq_data['reformulation'] = line.replace('Reformulation:', '').strip()
        
        cq_list.append(cq_data)
    
    return cq_list


def load_csv_data(csv_path: str = "d:/GitHub/IDEA2/assets/us_personas/askcq_dataset.csv") -> pd.DataFrame:
    """
    Load the CSV data containing scores and votes.
    
    Parameters
    ----------
    csv_path : str
        Path to the askcq_dataset.csv file
    
    Returns
    -------
    pd.DataFrame
        The loaded dataframe
    """
    return pd.read_csv(csv_path, dtype=str)


def get_score_and_votes(df: pd.DataFrame, cq_id: str) -> tuple:
    """
    Get score and votes for a specific CQ ID from the dataframe.
    
    Parameters
    ----------
    df : pd.DataFrame
        The CSV dataframe
    cq_id : str
        The ID to look up
    
    Returns
    -------
    tuple
        (score, votes) as strings, or (None, None) if not found
    """
    row = df[df['id'] == cq_id]
    if not row.empty:
        score = row['score'].values[0]
        votes = row['votes'].values[0]
        return (score if pd.notna(score) else None, 
                votes if pd.notna(votes) else None)
    return (None, None)


def find_page_by_title(database_id: str, title: str) -> str:
    """
    Find a page in the database by matching its title.
    
    Parameters
    ----------
    database_id : str
        The Notion database ID
    title : str
        The title to search for (reformulation text)
    
    Returns
    -------
    str or None
        The page ID if found, None otherwise
    """
    try:
        response = notion.databases.query(
            database_id=database_id,
            filter={
                "property": "CQ",
                "title": {
                    "equals": title
                }
            }
        )
        
        if response["results"]:
            return response["results"][0]["id"]
        return None
    except Exception as e:
        print(f"Error finding page '{title}': {e}")
        return None


def update_recap_field(page_id: str, recap_text: str) -> bool:
    """
    Update the Recap field for a given page.
    
    Parameters
    ----------
    page_id : str
        The Notion page ID
    recap_text : str
        The text to add to the Recap field
    
    Returns
    -------
    bool
        True if successful, False otherwise
    """
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "Recap": {
                    "rich_text": [
                        {
                            "text": {
                                "content": recap_text
                            }
                        }
                    ]
                }
            }
        )
        return True
    except Exception as e:
        print(f"Error updating page {page_id}: {e}")
        return False


def push_recap_to_notion(cq_info: list, df: pd.DataFrame):
    """
    Loop through CQs and update Recap field in Notion.
    
    Parameters
    ----------
    cq_info : list
        List of dictionaries containing CQ information
    df : pd.DataFrame
        DataFrame containing score and votes data
    """
    successful = 0
    not_found = 0
    failed = 0
    
    for cq in tqdm(cq_info, desc="Updating Notion pages"):
        reformulation = cq['reformulation']
        original_cq = cq['original_cq']
        comment = cq['comment']
        cq_id = cq['id']
        
        # Get score and votes from CSV
        score, votes = get_score_and_votes(df, cq_id)
        
        # Create recap text combining original, comment, score, and votes
        recap_parts = [f"This CQ was reformulated from an original set of competency questions. The original CQ was: {original_cq}"]
        
        if comment:
            recap_parts.append(f"Feedback for the original CQ was: {comment}")
        if not comment:
            recap_parts.append("No comments or feedback were provided for the original CQ.")
        
        if score is not None:
            recap_parts.append(f"The score (from a majority vote) was: {score}")
        
        if votes is not None:
            recap_parts.append(f"The original CQ received {votes} votes.")
        
        recap_text = "\n".join(recap_parts)
        
        # Find the page by reformulation title
        page_id = find_page_by_title(notiondb, reformulation)
        
        if page_id:
            # Update the Recap field
            if update_recap_field(page_id, recap_text):
                successful += 1
                print(f"✓ Updated ID {cq_id}: {reformulation[:50]}...")
            else:
                failed += 1
        else:
            not_found += 1
            print(f"✗ Not found ID {cq_id}: {reformulation[:50]}...")
        
        # Rate limiting - Notion allows ~3 requests per second
        sleep(0.4)
    
    print(f"\n--- Summary ---")
    print(f"Successfully updated: {successful}")
    print(f"Not found: {not_found}")
    print(f"Failed to update: {failed}")


if __name__ == "__main__":
    # Load CSV data
    csv_path = "d:/GitHub/IDEA2/assets/us_personas/askcq_dataset.csv"
    df = load_csv_data(csv_path)
    
    # Load CQs from text file
    cqlist = read_cqs()
    
    # Push to Notion with score and votes
    push_recap_to_notion(cqlist, df)