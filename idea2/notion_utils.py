"""

This script writes the competency questions (CQs) to a Notion database given that the CQs are
already cleaned and stored in a text file. It uses the Notion API to create new entries in the specified database for each CQ.

This script also facilitates multiple use cases, such as adding remote CQs from a dataset, setting up LLM configurations in Notion,
"""

import os
import pprint
import json
from utils import get_key, subset_cqs_from_dataset, get_source_from_arr
from notion_client import Client
from tqdm import tqdm
from reformulate_cq import get_discussion_comments, get_name_from_id, pull_accepted
from time import sleep

from sklearn.metrics import cohen_kappa_score
import pandas as pd
from itertools import combinations
import krippendorff

import csv
from collections import defaultdict

notiontoken = None
llmdb = None
notiondb = None
NOTION_DATABASE_ID = None
notion = None

def _ensure_config():
    """Lazy initialization of Notion configuration."""
    global notiontoken, llmdb, notiondb, NOTION_DATABASE_ID, notion
    if notiontoken is None:
        notiontoken = get_key("notionkey")
        llmdb = get_key("notionllmdb")
        notiondb = get_key("notiondb")
        NOTION_DATABASE_ID = get_key("notiondb")
        notion = None  # Keep as None, use get_notion_client() instead



def get_notion_client():
    global notion
    if notion is None:
        notion = Client(auth=get_key("notionkey"))
    return notion


def get_current_iteration_from_dashboard() -> int:
    """
    
    Get the current iteration number from the Notion database (more robust than from the file generation number).

    Returns:
        int: The current iteration number.
    
    """
    from reformulate_cq import NOTION_DATABASE_ID
    
    all_results = []

    iteration_numbers = set()
    has_more = True
    next_cursor = None

    notion = get_notion_client()

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

    notion = get_notion_client()
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
            client=get_notion_client(),
            database_id=notiondb,
            cq=cq,
            iteration=get_current_iteration_from_dashboard(),
            generation_config="",
            src_documents="bme"
        )

def pull_cqs_with_high_score(min_score: int = 0, save_to_file: bool = True) -> list:
    """
    Pull all CQs from the Notion database that have a score value greater than min_score.
    
    Args:
        min_score (int): The minimum score threshold (default is 0, so pulls CQs with score > 0).
        save_to_file (bool): Whether to save the CQ data to a JSON-LD file (default is True).
    
    Returns:
        list: A list of dictionaries containing CQ data with keys:
              - 'id': The Notion page ID
              - 'cq': The competency question text
              - 'score': The score value
              - 'votes': The number of votes
              - 'iteration': The iteration number (if available)
              - 'source': The source documents (if available)
    """
    all_results = []
    has_more = True
    next_cursor = None
    
    print(f"Fetching CQs with score > {min_score} from Notion...")
    
    while has_more:
        response = notion.databases.query(
            **{
                "database_id": NOTION_DATABASE_ID,
                "filter": {
                    "property": "Score",
                    "number": {
                        "greater_than": min_score
                    }
                },
                "start_cursor": next_cursor,
                "page_size": 100
            }
        )
        all_results.extend(response["results"])
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")
    
    cqs_data = []
    
    # Extract context from source filenames (prefix before first underscore)
    # Get all unique sources first to determine context
    
    all_sources = set()
    for page in all_results:
        properties = page["properties"]
        if "Source" in properties and properties["Source"].get("multi_select"):
            for s in properties["Source"]["multi_select"]:
                all_sources.add(s["name"])
    
    # Get context from the first source filename
    context = get_source_from_arr(list(all_sources)) if all_sources else "unknown"
    print(f"Using @context: {context}")
    
    for page in tqdm(all_results, desc="Processing high-score CQs"):
        properties = page["properties"]
        
        # Extract CQ text
        cq_text = ""
        if "CQ" in properties and properties["CQ"]["title"]:
            cq_text = properties["CQ"]["title"][0]["text"]["content"]
        
        # Extract score
        score = None
        if "Score" in properties and properties["Score"].get("number") is not None:
            score = properties["Score"]["number"]
        
        # Extract votes
        votes = None
        if "Votes" in properties and properties["Votes"].get("number") is not None:
            votes = properties["Votes"]["number"]
        
        # Extract iteration (if available)
        iteration = None
        if "Iteration" in properties and properties["Iteration"].get("number") is not None:
            iteration = properties["Iteration"]["number"]
        
        # Extract source (if available)
        sources = []
        if "Source" in properties and properties["Source"].get("multi_select"):
            sources = [s["name"] for s in properties["Source"]["multi_select"]]
        
        cqs_data.append({
            "@context": context,
            "@type": "CompetencyQuestion",
            "id": page["id"],
            "text": cq_text,
            "score": score,
            "votes": votes,
            "iteration": iteration,
            "source": sources
        })
    
    print(f"Found {len(cqs_data)} CQs with score > {min_score}")
    
    # Save CQ data to JSON-LD file
    if save_to_file:
        output_path = os.path.join(os.getcwd(), "assets", "cqs", "cqs.jsonld")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cqs_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(cqs_data)} CQs to {output_path}")
    
    return cqs_data


def get_cqs_with_votes_for_kappa():
    """
    Query the Notion database to get all CQs with their ID, Iteration, Score, Votes,
    and Reformulates relation. Export to CSV format for Cohen's Kappa calculation.
    
    Uses the "Upvoted By" and "Downvoted By" Person fields to determine votes.
    
    Returns:
        Path to the CSV file with CQ information and human ratings (1 for upvote, 0 for downvote).
    """
    from reformulate_cq import NOTION_DATABASE_ID, get_name_from_id
    
    notion = get_notion_client()
    all_results = []
    has_more = True
    next_cursor = None
    
    # Query all pages from the database
    print("Fetching CQs from Notion database...")
    while has_more:
        response = notion.databases.query(
            **{
                "database_id": NOTION_DATABASE_ID,
                "start_cursor": next_cursor
            }
        )
        all_results.extend(response["results"])
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")
    
    print(f"Found {len(all_results)} CQs")
    
    # Map authors to H numbers
    author_to_h_number = {}
    h_counter = 1
    
    # Collect all data
    cq_data = []
    
    for page in tqdm(all_results, desc="Processing CQs"):
        page_id = page["id"]
        properties = page["properties"]
        
        # Extract basic properties
        cq_text = ""
        if "CQ" in properties and properties["CQ"]["title"]:
            cq_text = properties["CQ"]["title"][0]["text"]["content"]
        
        iteration = None
        if "Iteration" in properties and properties["Iteration"]["number"] is not None:
            iteration = properties["Iteration"]["number"]
        
        score = None
        if "Score" in properties and properties["Score"].get("formula"):
            formula_value = properties["Score"]["formula"]
            if formula_value.get("type") == "number" and formula_value.get("number") is not None:
                score = formula_value["number"]
        
        votes = None
        if "Votes" in properties and properties["Votes"].get("formula"):
            formula_value = properties["Votes"]["formula"]
            if formula_value.get("type") == "number" and formula_value.get("number") is not None:
                votes = formula_value["number"]
        
        # Get reformulates relation
        reformulates = []
        if "Reformulates" in properties and properties["Reformulates"]["relation"]:
            reformulates = [rel["id"] for rel in properties["Reformulates"]["relation"]]
        
        # Get upvoted by (Person field)
        upvoted_by = []
        if "Upvoted By" in properties and properties["Upvoted By"]["people"]:
            upvoted_by = properties["Upvoted By"]["people"]
        
        # Get downvoted by (Person field)
        downvoted_by = []
        if "Downvoted By" in properties and properties["Downvoted By"]["people"]:
            downvoted_by = properties["Downvoted By"]["people"]
        
        # Process upvotes
        for person in upvoted_by:
            author_id = person["id"]
            author_name = get_name_from_id(author_id)
            
            # Assign H number to author if not already assigned
            if author_name not in author_to_h_number:
                author_to_h_number[author_name] = f"H{h_counter}"
                h_counter += 1
            
            cq_data.append({
                "CQ_ID": page_id,
                "CQ_Text": cq_text,
                "Iteration": iteration,
                "Score": score,
                "Votes": votes,
                "Reformulates": ",".join(reformulates) if reformulates else "",
                "Author": author_to_h_number[author_name],
                "Author_Name": author_name,
                "Vote": 1
            })
        
        # Process downvotes
        for person in downvoted_by:
            author_id = person["id"]
            author_name = get_name_from_id(author_id)
            
            # Assign H number to author if not already assigned
            if author_name not in author_to_h_number:
                author_to_h_number[author_name] = f"H{h_counter}"
                h_counter += 1
            
            cq_data.append({
                "CQ_ID": page_id,
                "CQ_Text": cq_text,
                "Iteration": iteration,
                "Score": score,
                "Votes": votes,
                "Reformulates": ",".join(reformulates) if reformulates else "",
                "Author": author_to_h_number[author_name],
                "Author_Name": author_name,
                "Vote": 0
            })
    
    # Write to CSV
    output_file = os.path.join(os.getcwd(), "cq_votes_kappa.csv")
    
    if cq_data:
        fieldnames = ["CQ_ID", "CQ_Text", "Iteration", "Score", "Votes", "Reformulates", "Author", "Author_Name", "Vote"]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(cq_data)
        
        print(f"\nData exported to {output_file}")
        print(f"Total entries: {len(cq_data)}")
        print(f"Unique authors: {len(author_to_h_number)}")
        print("\nAuthor mapping:")
        for author, h_num in sorted(author_to_h_number.items(), key=lambda x: int(x[1][1:])):
            print(f"  {h_num}: {author}")
    else:
        print("No vote data found.")
    
    return output_file


def calculate_kappa_from_csv(csv_file=None):
    """
    Calculate Cohen's Kappa score from the CSV file containing vote data.
    Only uses CQs that were rated by ALL annotators (intersection).
    Also calculates Krippendorff's Alpha.
    
    Args:
        csv_file: Path to the CSV file. If None, uses the default 'cq_votes_kappa.csv'
    
    Returns:
        Dictionary containing kappa scores for all rater pairs, average kappa, and Krippendorff's Alpha
    """
    
    if csv_file is None:
        csv_file = os.path.join(os.getcwd(), "cq_votes_kappa.csv")
    
    if not os.path.exists(csv_file):
        print(f"CSV file not found: {csv_file}")
        print("Run get_cqs_with_votes_for_kappa() first to generate the data.")
        return None
    
    # Load the data
    df = pd.read_csv(csv_file)
    
    print(f"\nLoaded {len(df)} vote records")
    print(f"Unique CQs: {df['CQ_ID'].nunique()}")
    print(f"Unique raters: {df['Author'].nunique()}")
    print(f"\nRaters: {sorted(df['Author'].unique())}")
    
    # Check for duplicates (same CQ_ID + Author combination)
    duplicates = df.groupby(['CQ_ID', 'Author']).size()
    if (duplicates > 1).any():
        print(f"\nWARNING: Found duplicate votes!")
        duplicate_pairs = duplicates[duplicates > 1]
        print(f"Number of CQ-Author pairs with multiple votes: {len(duplicate_pairs)}")
        print(duplicate_pairs.head())
    else:
        print(f"\nNo duplicate votes found - each annotator voted once per CQ")
    
    # Pivot the data so each CQ is a row and each rater is a column
    pivot_df = df.pivot_table(
        index='CQ_ID',
        columns='Author',
        values='Vote',
        aggfunc='first'  # In case of duplicates, take the first
    )
    
    print(f"\nPivot table shape (all CQs): {pivot_df.shape}")
    print(f"Total CQs: {len(pivot_df)}")
    
    print(f"\nVotes per rater (before filtering):")
    vote_counts = pivot_df.count()
    print(vote_counts)
    
    # Show missing votes per rater
    print(f"\nMissing votes per rater:")
    for rater in pivot_df.columns:
        missing = len(pivot_df) - vote_counts[rater]
        print(f"  {rater}: {missing} CQs not voted on")
    
    # Filter to only CQs rated by ALL annotators
    pivot_df_complete = pivot_df.dropna()
    
    print(f"\n{'='*60}")
    print(f"Filtering to CQs rated by ALL annotators")
    print(f"{'='*60}")
    print(f"CQs rated by all annotators: {len(pivot_df_complete)}")
    print(f"CQs excluded (incomplete ratings): {len(pivot_df) - len(pivot_df_complete)}")
    
    if len(pivot_df_complete) == 0:
        print("\nNo CQs were rated by all annotators!")
        return None
    
    # Show which raters are missing on excluded CQs
    if len(pivot_df) - len(pivot_df_complete) > 0:
        print(f"\nBreakdown of incomplete CQs:")
        incomplete_cqs = pivot_df[pivot_df.isna().any(axis=1)]
        for rater in incomplete_cqs.columns:
            num_missing = incomplete_cqs[rater].isna().sum()
            if num_missing > 0:
                print(f"  {rater}: missing votes on {num_missing} of the excluded CQs")
    
    print(f"\nRating distribution per rater (complete CQs only):")
    upvote_counts = pivot_df_complete.sum()
    downvote_counts = len(pivot_df_complete) - upvote_counts
    print(f"\nUpvotes per rater:")
    print(upvote_counts.astype(int))
    print(f"\nDownvotes per rater:")
    print(downvote_counts.astype(int))
    print(f"\nTotal votes per rater (should all be {len(pivot_df_complete)}):")
    print((upvote_counts + downvote_counts).astype(int))
    
    # Get all rater pairs
    raters = list(pivot_df_complete.columns)
    
    if len(raters) < 2:
        print("\nNeed at least 2 raters to calculate Cohen's Kappa")
        return None
    
    # Calculate kappa for each pair of raters
    kappa_scores = {}
    
    print(f"\n{'='*60}")
    print("Cohen's Kappa Scores (Pairwise - Complete Cases Only)")
    print(f"{'='*60}")
    
    for rater1, rater2 in combinations(raters, 2):
        # Get ratings for this pair (all should be complete now)
        common_ratings = pivot_df_complete[[rater1, rater2]]
        
        if len(common_ratings) < 2:
            print(f"\n{rater1} vs {rater2}: Not enough common ratings ({len(common_ratings)})")
            kappa_scores[f"{rater1}_vs_{rater2}"] = None
            continue
        
        # Calculate Cohen's Kappa
        kappa = cohen_kappa_score(common_ratings[rater1], common_ratings[rater2])
        kappa_scores[f"{rater1}_vs_{rater2}"] = kappa
        
        # Interpretation
        if kappa < 0:
            interpretation = "Poor (less than chance agreement)"
        elif kappa < 0.20:
            interpretation = "Slight"
        elif kappa < 0.40:
            interpretation = "Fair"
        elif kappa < 0.60:
            interpretation = "Moderate"
        elif kappa < 0.80:
            interpretation = "Substantial"
        else:
            interpretation = "Almost Perfect"
        
        print(f"\n{rater1} vs {rater2}:")
        print(f"  Common CQs rated: {len(common_ratings)}")
        print(f"  Kappa: {kappa:.4f} ({interpretation})")
    
    # Calculate average kappa
    valid_kappas = [k for k in kappa_scores.values() if k is not None]
    
    if valid_kappas:
        avg_kappa = sum(valid_kappas) / len(valid_kappas)
        print(f"\n{'='*60}")
        print(f"Average Kappa (across all pairs): {avg_kappa:.4f}")
        print(f"{'='*60}")
        
        kappa_scores['average_kappa'] = avg_kappa
    
    # Calculate Krippendorff's Alpha
    print(f"\n{'='*60}")
    print("Krippendorff's Alpha")
    print(f"{'='*60}")
    
    # Prepare data for Krippendorff's Alpha (needs format: raters x items)
    # Convert to numpy array with raters as rows and items (CQs) as columns
    reliability_data = pivot_df_complete.T.values
    
    try:
        alpha = krippendorff.alpha(reliability_data=reliability_data, level_of_measurement='nominal')
        print(f"\nKrippendorff's Alpha: {alpha:.4f}")
        
        # Interpretation for Krippendorff's Alpha
        if alpha < 0:
            alpha_interpretation = "Poor (less than chance agreement)"
        elif alpha < 0.20:
            alpha_interpretation = "Slight"
        elif alpha < 0.40:
            alpha_interpretation = "Fair"
        elif alpha < 0.67:
            alpha_interpretation = "Moderate (tentative conclusions)"
        elif alpha < 0.80:
            alpha_interpretation = "Substantial (definite conclusions)"
        else:
            alpha_interpretation = "Almost Perfect"
        
        print(f"Interpretation: {alpha_interpretation}")
        print(f"\nNote: Krippendorff's Alpha ≥ 0.80 is required for definitive conclusions")
        print(f"      Alpha ≥ 0.67 is acceptable for tentative conclusions")
        
        kappa_scores['krippendorff_alpha'] = alpha
    except Exception as e:
        print(f"\nError calculating Krippendorff's Alpha: {e}")
        kappa_scores['krippendorff_alpha'] = None
    
    # Save results to file
    results_file = os.path.join(os.getcwd(), "kappa_results.txt")
    with open(results_file, 'w') as f:
        f.write("Inter-Rater Reliability Scores\n")
        f.write("="*60 + "\n\n")
        f.write(f"CQs rated by all annotators: {len(pivot_df_complete)}\n")
        f.write(f"Number of annotators: {len(raters)}\n\n")
        
        f.write("Cohen's Kappa Scores (Pairwise)\n")
        f.write("-"*60 + "\n")
        for pair, score in kappa_scores.items():
            if pair not in ['average_kappa', 'krippendorff_alpha'] and score is not None:
                f.write(f"{pair}: {score:.4f}\n")
        if 'average_kappa' in kappa_scores:
            f.write(f"\nAverage Kappa: {kappa_scores['average_kappa']:.4f}\n")
        
        if 'krippendorff_alpha' in kappa_scores and kappa_scores['krippendorff_alpha'] is not None:
            f.write(f"\n{'='*60}\n")
            f.write(f"Krippendorff's Alpha: {kappa_scores['krippendorff_alpha']:.4f}\n")
    
    print(f"\nResults saved to: {results_file}")
    
    return kappa_scores


if __name__ == "__main__":
    # remote_add_cqs(os.path.join(os.getcwd(), "assets", "us_personas", "askcq_dataset.csv"), 23)
    csv_file = get_cqs_with_votes_for_kappa()
    calculate_kappa_from_csv(csv_file)
