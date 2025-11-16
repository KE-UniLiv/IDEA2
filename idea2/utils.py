"""
Collects utility functions for the xaniml package.
"""

import yaml
import os
import logging
import time
import json
import argparse
import hashlib
from pathlib import Path
import questionary
import glob
import pandas as pd
import shutil
import tkinter as tk
from tkinter import filedialog



# If running from a scirpt, use the script's directory to find the config file
config_path = os.path.join(os.path.dirname(__file__), "api_config.yml")


def select_files_with_dialog():
    """
    Open a native file dialog for file selection and copy to assets folder.
    Uses tkinter.filedialog for GUI file picking.
    """
    # Hide the root tkinter window
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    print(os.getcwd())
    
    # Select multiple files using native file dialog
    files = filedialog.askopenfilenames(
        title="Select files to import for IDEA2",
        filetypes=[
            ("All files", "*.*"),
            ("Schema files", "*.xsd *.xml"),
            ("JSON files", "*.json *.jsonld"),
            ("Text files", "*.txt *.md"),
        ]
    )
    
    if not files:
        print("No files selected.")
        root.destroy()
        return
    
    # Get the assets directory - normalize the path
    assets_dir = os.path.normpath(os.path.join(os.getcwd(), "assets"))
    
    # Ask user to select destination folder within assets using native dialog
    dest_folder = filedialog.askdirectory(
        title="Select destination folder in assets",
        initialdir=assets_dir
    )
    
    root.destroy()
    
    if not dest_folder:
        print("No destination folder selected.")
        return
    
    # Normalize the destination path for comparison
    dest_folder = os.path.normpath(dest_folder)
    
    # Verify destination is within assets
    # Use os.path.commonpath to check if dest_folder is under assets_dir
    try:
        common_path = os.path.commonpath([assets_dir, dest_folder])
        if common_path != assets_dir:
            print(f"Error: Destination must be within the assets folder.")
            print(f"  Assets dir: {assets_dir}")
            print(f"  Selected: {dest_folder}")
            return
    except ValueError:
        # Paths are on different drives
        print(f"Error: Destination must be within the assets folder.")
        return
    
    # Copy files to destination
    copied_count = 0
    for file_path in files:
        try:
            filename = os.path.basename(file_path)
            dest_path = os.path.join(dest_folder, filename)
            
            # Check if file already exists
            if os.path.exists(dest_path):
                overwrite = questionary.confirm(
                    f"File '{filename}' already exists. Overwrite?"
                ).ask()
                if not overwrite:
                    print(f"Skipped: {filename}")
                    continue
            
            shutil.copy2(file_path, dest_path)
            print(f"✓ Copied: {filename}")
            copied_count += 1
            
        except Exception as e:
            print(f"✗ Error copying {filename}: {e}")
    
    print(f"\nSuccessfully copied {copied_count}/{len(files)} files to:")
    print(f"  {os.path.relpath(dest_folder, os.getcwd())}")

def get_key(service, config_file="api_config.yml"):
    """
    Get the API key for the given service from a config file in YAML format. For
    example, `get_key("openai")` will return the OpenAI API key.
    """

    if not os.path.exists(config_file):
        # If the config file does not exist from some entry point, use a path correction
        config_file = config_path

    ## -- Read the YML file first and get the right entry
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    return config[service]["key"]

def update_key(service, new_key, config_file="api_config.yml"):
    """
    Update the API key for the given service in the config file.
    
    Parameters
    ----------
    service : str
        The name of the service (e.g., "openai").
    new_key : str
        The new API key to set.
    config_file : str
        The path to the config file. Defaults to "api_config.yml".
    
    Returns
    -------
    None
    """
    
    if not os.path.exists(config_file):
        # If the config file does not exist from some entry point, use a path correction
        config_file = config_path

    with open(config_file, "r") as f:
        config = yaml.safe_load(f)
    
    config[service]["key"] = new_key
    
    with open(config_file, "w") as f:
        yaml.safe_dump(config, f)
        logging.info(f"Updated API key for {service} in {config_file}")


def getSchemas():
    """
    Gets schemas from either the schema or us_personas folder based on user selection.
    Allows users to select specific files ending in .xsd, .xml, or .md.

    Returns:
        tuple: A tuple containing the combined selected schemas as strings, and a list of selected filenames.
    """
    
    ## -- Ask user which folder to look in
    folder_choice = questionary.select(
        "Which folder would you like to look for schemas in?",
        choices=[
            "assets/schema",
            "assets/us_personas"
        ]
    ).ask()
    
    if not folder_choice:
        print("No folder selected. Exiting.")
        return None, None
    
    ## -- Build the full path
    folder_path = os.path.join(os.getcwd(), folder_choice)
    
    ## -- Check if folder exists
    if not os.path.exists(folder_path):
        logging.error(f"Folder {folder_path} does not exist.")
        return None, None
    
    ## -- Find all files with the specified extensions
    valid_extensions = ['.xsd', '.xml', '.md']
    available_files = []
    
    try:
        for filename in os.listdir(folder_path):
            if any(filename.endswith(ext) for ext in valid_extensions):
                available_files.append(filename)
    except OSError as e:
        logging.error(f"Error reading folder {folder_path}: {e}")
        return None, None
    
    if not available_files:
        print(f"No files with extensions {valid_extensions} found in {folder_path}")
        return None, None

    ## -- Let user select multiple files
    selected_files = questionary.checkbox(
        "Select the files you want to use as schemas:",
        choices=available_files
    ).ask()
    
    if not selected_files:
        print("No files selected. Exiting.")
        return None, None
    
    ## -- Read and combine the selected files
    combined_schemas = []
    file_names = []
    
    for filename in selected_files:
        file_path = os.path.join(folder_path, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                combined_schemas.append(f"{content}")
                file_names.append(filename)
                logging.info(f"Successfully loaded: {filename}")
        except FileNotFoundError as e:
            logging.error(f"File not found: {file_path}")
            continue
        except Exception as e:
            logging.error(f"Error reading {file_path}: {e}")
            continue

    if not combined_schemas:
        logging.error("No files could be read successfully.")
        return None, None

    # -- Sort the schemas, this also ensures _persona comes before _us1
    combined_schemas.sort()

    ## -- Combine all schemas into a single string
    final_schema = "\n".join(combined_schemas)
    
    print(f"Successfully loaded {len(selected_files)} schema files:")
    for filename in selected_files:
        print(f"  - {filename}")
    
    return final_schema, selected_files, file_names

def check_model(model):
    """
    Resolve the file path for the history based on the model name given or used in an iteration.

    Args:
        model (str): The name of the model used.

    Returns:
        str: The file path where the history will be saved.
    """


    if model in ["models/gemini-2.5-flash", "models/gemini-2.5-pro", "models/gemini-1.5-flash-latest"]:
        filepath = "gemini_history.json"
    elif model in ["models/openai-gpt-4", "models/openai-gpt-3.5-turbo"]:
        filepath = "gpt_history.json"
    else:
        raise ValueError(f"Unknown model: {model}. Please specify a valid model.")

    return filepath

def number_of_rejected_from_csv(filepath, restriction):
    df = pd.read_csv(filepath)

    filter = df[(df['score'] <= 0) & (df['set'] != restriction)]
    count = len(filter)

    print(f"Number of rejected competency questions (score <= 0) excluding set '{restriction}': {count}")
    return count

def get_info_from_first_iter():
    cqs_dir = os.path.join(os.getcwd(), "assets", "cqs")
    candidates = glob.glob(os.path.join(cqs_dir, "g01*.jsonld"))

    if not candidates:
        print("No g01*.jsonld files found in assets/cqs.")
        return None, None, None

    target_file = None
    for f in candidates:
        if os.path.basename(f) == "g01_cqs.jsonld":
            target_file = f
            break
    if not target_file:
        target_file = candidates[0]

    try:
        with open(target_file, "r", encoding="utf-8") as jf:
            data = json.load(jf)
        if isinstance(data, list) and data:
            context = data[0].get("@context")
            print(f"Extracted @context from {os.path.basename(target_file)}: {context}")
            return context, os.path.basename(target_file), target_file
        else:
            print(f"No @context field found in {os.path.basename(target_file)}")
            return None, None, None
    except Exception as e:
        print(f"Error reading {target_file}: {e}")
        return None, None, None

def subset_cqs_from_dataset(filepath, n, restriction) -> list:
    """
    Get a subset of competency questions from a CSV dataset based on score.
    Args:
        filepath (str): The path to the CSV file containing the dataset.
        n (int): The number of competency questions to retrieve.
    Returns:
        list: A list of competency questions with score >= 0.

    """
    df = pd.read_csv(filepath)

    filter = df[(df['score'] >= 0) & (df['set'] != restriction)].sample(n=n, random_state=42)
    cqs = filter['cq'].tolist()

    return cqs



def get_source_from_arr(arr: list) -> str:
    """
    Get a combined source document string from an array of source documents.

    Args:
        arr (list): A list of source document strings.

    Returns:
        str: A combined source document string.
    """
    valid_types = ["persona", "user_story", "us1", "us2", "us3", "core", "technique", "schema", "xmlschema"]
    for file in arr:
        if any(vtype in file for vtype in valid_types):
            result = file.split('_')[0] or file.split('-')[0]

    return result

def load_history_from_file(model) -> list:
    """
    Load the history of interactions with the Gemini model from a file.

    Args:
        model (str): The name of the model used, which determines the file path.

    Returns:
        list: A list of dictionaries containing the interaction history.
    
    """

    filepath = check_model(model)
    
    if not os.path.exists(filepath):
        logging.warning(f"History file {filepath} does not exist. Returning empty history.")
        return []
    

    with open(filepath, 'r') as f:
        content = f.read().strip()

        if not content:
            logging.warning(f"History file {filepath} is empty. Returning empty history.")
            return []
        
        history = json.loads(content)
    logging.info(f"History loaded from {filepath}")
    return history

def save_history_to_file(history, model):
    """
    Save the history of interactions with the Gemini model to a file.

    Args:
        history (list): A list of dictionaries containing the interaction history.
        model (str): The name of the model used, which determines the file path.

    Returns:
        None: The function saves the history to the specified file.
    
    """

    filepath = check_model(model)
    
    with open(filepath, 'w', encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    
    logging.info(f"History saved to {filepath}")

def parse_two(arg) -> tuple:
    """
    Parse a string containing two comma-separated integers.

    Args:
        arg (str): A string containing two comma-separated integers, e.g. "1,2" or "1, 2".

    Returns:
        tuple: A tuple containing the two integers.
    
    Raises:
        argparse.ArgumentTypeError: If the input is not in the correct format.
    """
    
    parts = arg.replace(" ", "").split(",")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("Must provide two comma-separated values, e.g. 1,2")
    
    return str(parts[0]), str(parts[1])

def help_config():

    os.system("CLS")

    print("\nConfiguration options (in this positional order):\n----------------------------------------------------------------------------------------------------------------")
    print("temperature: The temperature for the model (default: 0.2)")
    print("role: The role for the model (default: SYSTEM_ROLE_A) (options: SYSTEM_ROLE_A, SYSTEM_ROLE_B, SYSTEM_ROLE_C)")
    print("gemini_model: The model to use (default: models/gemini-2.5-flash)")
    print("out_definition: The output definition for competency questions (default: CQ_DEFINITION_A) (options: CQ_DEFINITION_A)")
    print("out_examples: The output examples for competency questions (default: CQ_EXAMPLE_A) (options: CQ_EXAMPLE_A, CQ_EXAMPLE_B, CQ_EXAMPLE_C)")
    print("out_instruction: The output instruction for competency questions (default: CQ_INSTRUCTION_C) (options: CQ_INSTRUCTION_A, CQ_INSTRUCTION_B, CQ_INSTRUCTION_C)\n")

def show_customhelp():
    """
    Print the custom help message for the script with more informative steps.

    Returns:
        None: This function prints the help message to the console.
    
    """

    os.system("CLS")
    steps = [
        "This is the help for IDEA2",
        "All arguments are optional, and the script will use default values if not provided.",
        "(Remember to use --save if you want anything to be saved)\n",
        "--find_rejected and --reformulate can be used together with --notion",
        "You can use --help to see available options for each argument.\n",
        "Also, remember to set your API keys in the api_config.yml file. You may also use --update_key <service>,<new_key> for this purpose.\n"
        "You may also use --show_services to see the available services and their string names in the config file.\n",
        "1. Run the script with the desired arguments.",
        "2. The script will extract competency questions using the specified model and prompt.",
    ]

    for line in steps:
        print(line)
        time.sleep(2)

def show_services():
    """
    Print the available services and their API keys from the config file.

    Returns:
        None: This function prints the services and their keys to the console.
    
    """

    if not os.path.exists(config_path):
        print(f"Config file {config_path} does not exist.")
        return

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    print("Available services:")
    for service in config.keys():
        print(service)

def hash_from_string(s: str) -> str:
    """
    Generate a hash from a string.

    Args:
        s (str): The input string to hash.

    Returns:
        str: The generated hash.
    
    """
    return hashlib.sha256(s.encode()).hexdigest()

def store_hash_text_combinations(s, filepath="assets/cqs/hash_text_tuples.json"):
    """
    Store a hash and text tuple in a JSON file.
    Args:
        s (str): The input string to hash and store.
        filepath (str): The path to the JSON file where the tuple will be stored.
    """
    hash_value = hash_from_string(s)

    # Load existing data
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        data = {}

    # Update with new hash-text tuple
    data[hash_value] = s

    # Save back to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def lookup_text_by_hash(hash_value, filepath="assets/cqs/hash_text_tuples.json"):
    """
    Lookup text by its hash from a JSON file.
    Args:
        hash_value (str): The hash value to look up.
        filepath (str): The path to the JSON file where the tuples are stored.
    """

    if not os.path.exists(filepath):
        print(f"File {filepath} does not exist.")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"File {filepath} is not a valid JSON.")
            return None

    return data.get(hash_value)

if __name__ == "__main__":
    score = number_of_rejected_from_csv(os.path.join(os.getcwd(), "assets", "us_personas", "askcq_dataset.csv"), 3)