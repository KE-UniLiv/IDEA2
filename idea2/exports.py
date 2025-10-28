"""

Module to export data from the workflow; the courier of information.

"""

import os
import json
import questionary
from datetime import datetime

def export_cqs_from_json_ld_files(cq_directory: str = os.path.join(os.getcwd(), "assets/cqs") ):
    """
    Export competency questions from JSON-LD files in the specified directory.
    Uses questionary to allow user selection of specific files or all files.

    Parameters
    ----------
    cq_directory : str
        The directory containing the JSON-LD files with competency questions.

    Returns
    -------
    list
        A list of competency questions extracted from the selected JSON-LD files.
    """
    cqs = []
    
    ## -- Check if directory exists
    if not os.path.exists(cq_directory):
        print(f"Directory {cq_directory} does not exist.")
        return cqs
    
    ## -- Find all .jsonld files in the directory
    jsonld_files = []
    for filename in os.listdir(cq_directory):
        if filename.endswith('.jsonld'):
            jsonld_files.append(filename)
    
    if not jsonld_files:
        print(f"No JSON-LD files found in {cq_directory}")
        return cqs
    
    ## -- Sort files for consistent ordering
    jsonld_files.sort()
    
    ## -- Ask user if they want all files or specific selection
    use_all_files = questionary.confirm(
        f"Do you want to process all {len(jsonld_files)} JSON-LD files? (select N to choose specific files)"
    ).ask()
    
    if use_all_files:
        files_to_process = jsonld_files
        print(f"Processing all {len(jsonld_files)} JSON-LD files...")
    else:
        ## -- Ask user to select specific files
        selected_choices = questionary.checkbox(
            "Select the JSON-LD files you want to export from:",
            choices=jsonld_files
        ).ask()
        
        if not selected_choices:
            print("No files selected. Exiting.")
            return cqs
        
        files_to_process = selected_choices
        print(f"Processing {len(files_to_process)} selected files...")
    
    ## -- Process each selected file
    for filename in files_to_process:
        file_path = os.path.join(cq_directory, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            ## -- Extract CQs from the JSON-LD structure
            # -- Assuming the structure has a list of items with "cq" or "@value" fields
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        ## -- Try different possible field names for the CQ text
                        cq_text = item.get('text')
                        if cq_text:
                            cqs.append({
                                'text': cq_text,
                                'source_file': filename,
                                'hash': item.get('@URI', ''),
                                'iteration': item.get('identifier', ''),
                                'model': item.get('belongsToModel', {}).get('name'),
                                'temperature': item.get('belongsToModel', {}).get('temperature')
                            })
            elif isinstance(data, dict):
                ## -- Handle single CQ or different JSON-LD structure
                cq_text = data.get('cq') or data.get('@value') or data.get('question') or data.get('text')
                if cq_text:
                    cqs.append({
                        'text': cq_text,
                        'source_file': filename,
                        'hash': item.get('@URI', ''),
                        'iteration': item.get('identifier', ''),
                        'model': item.get('belongsToModel', {}).get('name'),
                        'temperature': item.get('belongsToModel', {}).get('temperature')
                    })
                    
            print(f"  ✓ Processed {filename}")
            
        except json.JSONDecodeError as e:
            print(f"  ✗ Error parsing JSON in {filename}: {e}")
            continue
        except FileNotFoundError as e:
            print(f"  ✗ File not found: {filename}")
            continue
        except Exception as e:
            print(f"  ✗ Error processing {filename}: {e}")
            continue
    
    date_yyyy_mm_dd = datetime.now().strftime("%Y_%m_%d")
    with open(os.path.join(cq_directory, f"exported_cqs_{date_yyyy_mm_dd}.json"), 'w', encoding='utf-8') as outfile:
        json.dump(cqs, outfile, indent=2, ensure_ascii=False)
    
    print(f"\nSuccessfully extracted {len(cqs)} competency questions from {len(files_to_process)} files.")
    return cqs

if __name__ == "__main__":
    export_cqs_from_json_ld_files()