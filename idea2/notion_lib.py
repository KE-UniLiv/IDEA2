
import uuid
import json
from notion_client import Client
from pprint import pprint


def write_text(client, page_id, text, type):
    client.blocks.children.append(
        block_id=page_id,
        children=[
            {
                "object": "block",
                "type": type,
                type: {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": text
                            }
                        }
                    ]
                }
            }
        ]
    )


def write_dict_to_file_as_json(content, file_name):
    """
    A simple function to write a dictionary to a file as a JSON string.
    """
    content_as_json_str = json.dumps(content)
    with open(file_name, 'w') as f:
        f.write(content_as_json_str)

def read_text(client, page_id):
    """
    Read the text content of a page.
    """
    response = client.blocks.children.list(block_id=page_id)
    return response['results']

def safe_get(data, dot_chained_keys):
    '''
        {'a': {'b': [{'c': 1}]}}
        safe_get(data, 'a.b.0.c') -> 1
    '''
    keys = dot_chained_keys.split('.')
    for key in keys:
        try:
            if isinstance(data, list):
                data = data[int(key)]
            else:
                data = data[key]
        except (KeyError, TypeError, IndexError):
            return None
    return data


def read_rows(db_rows):

    simple_rows = []

    for row in db_rows['results']:
        user_id = safe_get(row, 'properties.UserId.title.0.plain_text')
        date = safe_get(row, 'properties.Date.date.start')
        event = safe_get(row, 'properties.Event.select.name')

        simple_rows.append({
            'user_id': user_id,
            'date': date,
            'event': event
        })
    # write_dict_to_file_as_json(simple_rows, 'simple_rows.json')
    return simple_rows
    


def create_simple_blocks_from_content(client, content):

    page_simple_blocks = []

    for block in content:

        block_id = block['id']
        block_type = block['type']
        has_children = block['has_children']
        rich_text = block[block_type].get('rich_text')

        if not rich_text:
            return

        simple_block = {
            'id': block_id,
            'type': block_type,
            'text': rich_text[0]['plain_text']
        }

        if has_children:
            nested_children = read_text(client, block_id)
            simple_block['children'] = create_simple_blocks_from_content(client, nested_children)

        page_simple_blocks.append(simple_block)

    return page_simple_blocks
    

def write_row(client, database_id, user_id, event, date):

    client.pages.create(
        **{
            "parent": {
                "database_id": database_id
            },
            'properties': {
                'UserId': {'title': [{'text': {'content': user_id}}]},
                'Event': {'select': {'name': event}},
                'Date': {'date': {'start': date}}
            }
        }
    )