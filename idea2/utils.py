"""
Collects utility functions for the xaniml package.
"""

import yaml
import os
import logging
import time
import json

# If running from a scirpt, use the script's directory to find the config file
config_path = os.path.join(os.path.dirname(__file__), "api_config.yml")

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


def getSchemas():
    """
    
    Gets the schemas for the ANIML core and technique from the assets/schema directory.

    Returns:
        tuple: A tuple containing the ANIML core schema and technique schema as strings.
    
    """

    try:
        animl_core_schema_path = os.path.join(os.getcwd(), "assets", "schema", "animl-core.xsd")
        animl_technique_schema_path = os.path.join(os.getcwd(), "assets", "schema", "animl-technique.xsd")

    except FileNotFoundError as e:
        logging.error(f"Schema files not found: {e}")
        return None, None


    animl_core_schema, animl_technique_schema = "", ""
    with open(animl_core_schema_path, "r") as f1, open(animl_technique_schema_path, "r") as f2:
        animl_core_schema, animl_technique_schema = f1.read(), f2.read()

    logging.info("Schema loaded successfully!")

    return animl_core_schema, animl_technique_schema

def load_history_from_file(filepath="gemini_history.json"):
    """
    Load the history of interactions with the Gemini model from a file.

    Args:
        filepath (str): The path to the file where the history is stored. Defaults to 'gemini_history.json'.

    Returns:
        list: A list of dictionaries containing the interaction history.
    
    """
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

def save_history_to_file(history, filepath="gemini_history.json"):
    """
    Save the history of interactions with the Gemini model to a file.

    Args:
        history (list): A list of dictionaries containing the interaction history.
        filepath (str): The path to the file where the history will be saved. Defaults to 'gemini_history.json'.

    Returns:
        None: The function saves the history to the specified file.
    
    """
    
    with open(filepath, 'w', encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    
    logging.info(f"History saved to {filepath}")

def help_config():
    """
    TODO: Identify whether this is suitable to be in utils.py


    Print the help message for the configuration.

    Returns:
        None: This function prints the help message to the console.
    
    """

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
        "This is the competency question extraction script.",
        "All arguments are optional, and the script will use default values if not provided.",
        "(Remember to use --save if you want anything to be saved)\n",
        "--find_rejected and --reformulate can be used together but only with no other arguments.",
        "You can use --help to see available options for each argument.\n",
        "1. Run the script with the desired arguments.",
        "2. The script will extract competency questions using the specified model and prompt.",
    ]

    for line in steps:
        print(line)
        time.sleep(2)