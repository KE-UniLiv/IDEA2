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
        "Also, remember to set your API keys in the api_config.yml file. You may also use --update_key <service>,<new_key> for this purpose.\n",
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