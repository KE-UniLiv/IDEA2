"""

Module to export data from the workflow; the courier of information.

"""

import os
import json
import questionary
from datetime import datetime
from urllib.parse import quote

def export_cqs_from_json_ld_files(cq_directory: str = os.path.join(os.getcwd(), "assets/cqs") ):
    """
    Export competency questions from JSON-LD files in the specified directory.
    Uses questionary to allow user selection of specific files or all files.
    Exports to valid JSON-LD using PROV-O, schema.org, and Croissant data model.

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
    timestamp_iso = datetime.now().isoformat()
    
    # Create valid JSON-LD structure with PROV-O, schema.org, Croissant, and OWLUnit
    json_ld_output = {
        "@context": {
            "@vocab": "http://schema.org/",
            "prov": "http://www.w3.org/ns/prov#",
            "cr": "http://mlcommons.org/croissant/",
            "@prefix owlunit": "<https://w3id.org/OWLunit/ontology/>",
            "CompetencyQuestion": "owlunit:CompetencyQuestion",
            "Dataset": "cr:Dataset",
            "RecordSet": "cr:RecordSet",
            "Field": "cr:Field",
            "wasGeneratedBy": "prov:wasGeneratedBy",
            "generatedAtTime": "prov:generatedAtTime",
            "wasAttributedTo": "prov:wasAttributedTo",
            "used": "prov:used",
            "Activity": "prov:Activity"
        },
        "@type": "Dataset",
        "@id": f"https://w3id.org/idea2/datasets/cqs_{date_yyyy_mm_dd}",
        "name": f"Competency Questions Export {date_yyyy_mm_dd}",
        "description": "A dataset of competency questions extracted from JSON-LD files with provenance metadata",
        "dateCreated": timestamp_iso,
        "dateModified": timestamp_iso,
        "version": "1.0",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "wasGeneratedBy": {
            "@type": "Activity",
            "@id": f"https://w3id.org/idea2/activities/export_{date_yyyy_mm_dd}",
            "name": "CQ Export Activity",
            "description": f"Export of competency questions from {len(files_to_process)} JSON-LD files",
            "startedAtTime": timestamp_iso,
            "endedAtTime": timestamp_iso,
            "used": [{"@id": f"https://w3id.org/idea2/files/{quote(f)}", "name": f} for f in files_to_process]
        },
        "distribution": {
            "@type": "DataDownload",
            "encodingFormat": "application/ld+json",
            "contentUrl": f"exported_cqs_{date_yyyy_mm_dd}.jsonld"
        },
        "cr:RecordSet": {
            "@type": "RecordSet",
            "@id": f"https://w3id.org/idea2/datasets/cqs_{date_yyyy_mm_dd}/recordset",
            "name": "Competency Questions",
            "description": "Collection of competency questions with metadata",
            "cr:Field": [
                {
                    "@type": "Field",
                    "name": "text",
                    "description": "The text of the competency question",
                    "dataType": "Text"
                },
                {
                    "@type": "Field",
                    "name": "source_file",
                    "description": "The source JSON-LD file from which the CQ was extracted",
                    "dataType": "Text"
                },
                {
                    "@type": "Field",
                    "name": "hash",
                    "description": "Unique identifier/hash for the competency question",
                    "dataType": "Text"
                },
                {
                    "@type": "Field",
                    "name": "iteration",
                    "description": "Iteration identifier for the CQ generation process",
                    "dataType": "Text"
                },
                {
                    "@type": "Field",
                    "name": "model",
                    "description": "The AI model used to generate the competency question",
                    "dataType": "Text"
                },
                {
                    "@type": "Field",
                    "name": "temperature",
                    "description": "The temperature parameter used during generation",
                    "dataType": "Float"
                }
            ],
            "data": []
        }
    }
    
    # Add CQs with provenance metadata using OWLUnit vocabulary
    for i, cq in enumerate(cqs):
        cq_entry = {
            "@type": "CompetencyQuestion",
            "@id": cq.get('hash', f"https://w3id.org/idea2/cqs/{i}"),
            "text": cq.get('text', ''),
            "source_file": cq.get('source_file', ''),
            "hash": cq.get('hash', ''),
            "iteration": cq.get('iteration', ''),
            "model": cq.get('model', ''),
            "temperature": cq.get('temperature', None),
            "wasGeneratedBy": {
                "@type": "Activity",
                "name": "CQ Generation",
                "wasAttributedTo": {
                    "@type": "SoftwareAgent",
                    "name": cq.get('model', 'Unknown Model')
                }
            },
            "generatedAtTime": timestamp_iso
        }
        json_ld_output["cr:RecordSet"]["data"].append(cq_entry)
    
    with open(os.path.join(cq_directory, f"exported_cqs_{date_yyyy_mm_dd}.jsonld"), 'w', encoding='utf-8') as outfile:
        json.dump(json_ld_output, outfile, indent=2, ensure_ascii=False)
    
    print(f"\nSuccessfully extracted {len(cqs)} competency questions from {len(files_to_process)} files.")
    return cqs

if __name__ == "__main__":
    export_cqs_from_json_ld_files()