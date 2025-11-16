import argparse
import os
import sys
import time
import questionary
import json

from tqdm import tqdm

from cq_json_ld import cq_to_json_ld
from reformulate_cq import (
    store_handled, get_cqs_from_file_as_strings, reformulate_cqs,
    get_rejected_cqs_from_file, store_pulled, validate_reformulated,
    pull_accepted, pull_rejected, cqs_from_csv
)
from cq_extraction import (
    get_llm_instance, save_llm_insatance, run_cq_extraction, cq_to_txt,
    clean_llm_output, configure_prompt, update_config, config, geminikey, get_notion_client, NOTION_DATABASE_ID,
    remove_local_ids_from_reformulations
)
from generation_utils import get_generation_number
from notion_utils import (
    get_cqs_from_file, llm_setup_to_notion, write_row, archive_all_pages
)

from utils import (
    get_key, update_key, getSchemas, 
    load_history_from_file, save_history_to_file,
    parse_two, show_customhelp, show_services,
    store_hash_text_combinations, select_files_with_dialog, get_source_from_arr
)
from cq_measures import run_simple_similarity_analysis
from cq_linkage import link_reformulations, get_page_id_by_title, src_cq_uuid

r"""

CLI interface for running the competency question extraction and storing results in Notion.

Usage:

    Pre-requisites:
        Ensure that all keys are filled in api_config.yml (you may update this with --update_key <service>,<new_key>)
        Ensure that the requirements are installed (see requirements.txt)

    
    (1): CD into the repo's directory:
        cd x:\IDEA2\idea2

    (2): Run the script with desired arguments:
        python idea2/runner.py [--model MODEL_NAME] [--temperature TEMPERATURE] [--role ROLE] [--save] [--notion] [--generation GENERATION_LABEL]

    note:
        All of these arguments are optional, and the script will use default values if not provided.

"""

def main():
    parser = argparse.ArgumentParser(description="Extract and store CQs using LLMs and Notion.")


    # -- TODO: 
    # (1) Use a source type to resolve new schemas ie --update_schema_to [path/to/schema1, path/to/schema2] then saves as current schema(s)
    # -  Then use --use_source [schema / ontology / user stories]
    # --


    parser.add_argument('--model', type=str, default="models/gemini-2.5-flash", help='Model name\n (Options: models/gemini-2.5-flash, models/gemini-2.5-pro, models/gemini-1.5-flash-latest, models/openai-gpt-4)')
    parser.add_argument('--temperature', type=float, default=0.2, help='LLM temperature\n (Options: 0.0 to 1.0) (Default: 0.2)')
    parser.add_argument('--role', type=str, default="SYSTEM_ROLE_A", help='Role for the LLM\n (Options: SYSTEM_ROLE_A, SYSTEM_ROLE_B, SYSTEM_ROLE_C)')
    parser.add_argument('--instruction', type=str, default="CQ_INSTRUCTION_A", help='Instruction for the LLM\n (Options: CQ_INSTRUCTION_A, CQ_INSTRUCTION_B, CQ_INSTRUCTION_C')
    parser.add_argument('--example', type=str, default="CQ_EXAMPLE_A", help='Give examples of CQs for the LLM\n (Options: CQ_EXAMPLE_A, CQ_EXAMPLE_B, CQ_EXAMPLE_C, CQ_ACCEPTED_CQS)')
    parser.add_argument('--generation', type=str, default=None, help='Generation label (auto if not set manually)')
    parser.add_argument('--update_key', type=str, default=None, help='Update the API key in api_config.yml (input: <service>,<new key value>)')

    parser.add_argument('--imports', action='store_true', help='Select files to copy using a text-based interface')
    parser.add_argument('--reformulate_from_first_set', action='store_true', help='Reformulate CQs when you already have some data stored. Start from iteration 2 without prior context.')
    parser.add_argument('--save', action='store_true', help='Save CQs to file (jsonld format)')
    parser.add_argument('--nolimit', action='store_true', help='Remove the limit on number of CQs to extract')
    parser.add_argument('--notion', action='store_true', help='Upload CQs to Notion')
    parser.add_argument('--reformulate', action='store_true', help='Reformulate CQs using rejected CQs as input (Note: run with --find_rejected to find rejected CQs first, then run with --reformulate to reformulate them)')
    parser.add_argument('--find_rejected', action='store_true', help='Find rejected CQs in Notion and store (Note: run as the only argument ie python runner.py --find_rejected)')
    parser.add_argument('--find_accepted', action='store_true', help='Find accepted CQs in Notion and store/refresh (Note: Ideally run as the only argument ie python runner.py --find_accepted)')
    parser.add_argument('--usage_help', action='store_true', help='Show a more comprehensive help message with usage instructions')
    parser.add_argument('--show_prompt', action='store_true', help='Show the prompts used for CQ extraction and reformulation')
    parser.add_argument('--show_services', action='store_true', help='Show the available services in api_config.yml')
    parser.add_argument('--archive', action='store_true', help='Archive all pages in the Notion database (use with caution, as this action is irreversible)')
    args = parser.parse_args()

    if args.show_services:
        show_services()
        sys.exit(0)

    if args.imports:
        select_files_with_dialog()
        sys.exit(0)

    if args.reformulate_from_first_set and args.reformulate:
        print("Error: --reformulate_from_first_set and --reformulate cannot be used together.")
        sys.exit(1)

    if len(sys.argv) == 1:
        print("No arguments provided. Use --help or --usage_help for usage information.")
        sys.exit(1)

    if args.update_key:
        service, newkey = parse_two(args.update_key)
        update_key(service, newkey)
        sys.exit(0)

    if args.usage_help:
        show_customhelp()
        sys.exit(0)

    if args.find_accepted:
        accepted_cqs = pull_accepted()
        store_pulled(accepted_cqs, typeof="accepted")
        sys.exit(0)

    if args.archive:
        if questionary.confirm("Are you sure you want to archive (delete) all pages (entries) in the Notion database? This action is irreversible.").ask():
            archive_all_pages(get_key("notiondb"))
        sys.exit(0)

    if args.nolimit:
        update_config(limit="")

    if args.find_rejected:
        rejected_cqs = pull_rejected()
        store_pulled(rejected_cqs, typeof="rejected")
        sys.exit(0) if not args.reformulate else print("Please run with --reformulate and --save to reformulate the rejected CQs and thus save to notion.")

    cqs = ""
    reformulated = False

    modelname = args.model if args.model else config["gemini_model"]
    print(f"Using model: {modelname}")

    combined, _, filename = getSchemas()

    history = load_history_from_file(modelname)
    schema_in_history = any(combined in h["content"] for h in history)

    if not args.reformulate_from_first_set:
        update_config(
            gemini_model=args.model if args.model else config["gemini_model"],
            temperature=args.temperature if args.temperature else config["temperature"],
            role=args.role if args.role else config["role"],
            out_instruction=args.instruction if args.instruction else config["out_instruction"],
            out_examples=args.example if args.example else config["out_examples"],
            limit=""
        )

        model = get_llm_instance(
        config["gemini_model"],
        api_key=geminikey,
        role=config["role"],
        temperature=config["temperature"]
    )

    generation, currgeneration = get_generation_number()
    currgeneration += 1

    if not args.reformulate and not args.find_rejected and not args.reformulate_from_first_set:
        prompt, combined_schemas, source = configure_prompt(
            role=config["role"],
            out_definition=config["out_definition"],
            out_examples=config["out_examples"],
            out_instruction=config["out_instruction"],
            limit=config["limit"],
            schema=combined,
            schema_names=filename,
            ignore_schemas=True if schema_in_history else False
        )

        formattedprompt = "\n".join([
            config['role'],
            config['out_definition'],
            config['out_examples'],
            config['out_instruction'],
            config['limit'],
            combined_schemas if not schema_in_history else ''
        ])
        
        history.append({"role": "user", "content": formattedprompt}) 

        if history:
            prompt_str = "\n".join([h["content"] for h in history])
            cqs = run_cq_extraction(model, prompt=prompt_str)
        else:
            cqs = run_cq_extraction(model, prompt=prompt)

        cleaned_cqs = clean_llm_output(cqs) if cqs else print("No CQs extracted, as no rejected CQs were found. Please run with --find_rejected to find rejected CQs first, then run with --reformulate to reformulate them.")
        
        for q in cleaned_cqs:
            history.append({"role": "assistant", "content": q})
            store_hash_text_combinations(q)

        save_history_to_file(history, modelname)

    if args.reformulate:
        update_config(out_instruction="CQ_INSTRUCTION_REFORMULATE", 
                      out_definition="get_cq_evaluation_definition", 
                      out_examples="CQ_ACCEPTED")

        reformulated = True

        accepted_cqs = pull_accepted()
        rejectcqs = pull_rejected()

        prompt, _, source = configure_prompt(
            role=config["role"],
            out_definition=config["out_definition"],
            out_examples=config["out_examples"],
            out_instruction=config["out_instruction"],
            schema=combined,
            schema_names=filename,
            ignore_schemas=True if schema_in_history else False
        )

        formattedprompt = "\n".join([
            config['out_definition'],
            config['out_examples'],
            config['out_instruction'],
        ])

        print(f"Formatted prompt for reformulation:\n{formattedprompt}\n") if args.show_prompt else None
        
        history.append({"role": "user", "content": (
            formattedprompt + 
                         json.dumps(rejectcqs, indent=2, ensure_ascii=False)
        )
        }) 

        if history:
            prompt_str = "\n".join([h["content"] for h in history])
            cqs = reformulate_cqs(model, prompt=prompt_str, cqs=rejectcqs)
        else:
            raise ValueError("No history found. There must be evidence of history to reformulate from.")
        
        cleaned_cqs = clean_llm_output(cqs) if cqs else None
        for q in cleaned_cqs:
            history.append({"role": "assistant", "content": q})

            store_hash_text_combinations(q)

    if args.reformulate_from_first_set:
        update_config(
            gemini_model=args.model if args.model else config["gemini_model"],  
            temperature=args.temperature if args.temperature else config["temperature"],  
            role=args.role if args.role else config["role"], 
            out_instruction="get_cq_evaluation_definition_bme",
            out_examples="",
            limit=""  
        )   
    
        model = get_llm_instance(
            modelname,
            api_key=geminikey,
            role=config["role"],
            temperature=config["temperature"]
        )

        reformulated = True
        rejectcqs = cqs_from_csv(os.path.join(os.getcwd(), "assets", "us_personas", "askcq_dataset.csv"))

        prompt, _, source = configure_prompt(
            role=config["role"],
            out_definition=config["out_definition"],
            out_examples=config["out_examples"],
            out_instruction=config["out_instruction"],
            schema=combined,
            schema_names=filename,
            limit=config["limit"],
            ignore_schemas=True if schema_in_history else False
        )

        formattedprompt = "\n".join([
            config['out_definition'],
            config['out_examples'],
            config['out_instruction'],
            config['limit'],
            combined if not schema_in_history else ''
        ])

        print(f"Formatted prompt for reformulation:\n{formattedprompt}\n") if args.show_prompt else None
        
        history.append({"role": "user", "content": (
            formattedprompt + "\n\n Here are the original competency questions with the data on their score, IDs, comments and votes: \n\n" +
            json.dumps(rejectcqs, indent=2, ensure_ascii=False)
        )}) 

        if history:
            prompt_str = "\n".join([h["content"] for h in history])  
            cqs = reformulate_cqs(model, prompt=prompt_str, cqs=rejectcqs)
        else:
            raise ValueError("No history found. There must be evidence of history to reformulate from.")
        
        ## -- With ID vs without ID
        cleaned_cqs = clean_llm_output(cqs) if cqs else None

        if args.save:
            outdir = os.path.join(os.getcwd(), "assets", "cqs")
            jsonld_path = os.path.join(outdir, f"{generation}.jsonld") if not args.reformulate else os.path.join(outdir, f"{generation}_reformulated.jsonld")
            naincludedcqs = cleaned_cqs.copy()

            cleaned_cqs = validate_reformulated(cleaned_cqs)
            cq_to_json_ld(cleaned_cqs, jsonld_path, filename)
            cq_to_txt(cleaned_cqs, os.path.join(outdir, f"{generation}_with_id_linkages.txt")) if not args.reformulate else None
        
        ## -- Now remvoe the ID after saving it locally
        cleaned_cqs = remove_local_ids_from_reformulations(cleaned_cqs)

        for q in cleaned_cqs:
            history.append({"role": "assistant", "content": q})

            store_hash_text_combinations(q)
    save_history_to_file(history, modelname)
    print(formattedprompt) if args.show_prompt else None

    if not args.reformulate:
        
        cleaned_cqs = run_simple_similarity_analysis(
            cleaned_cqs)

    ## -- Save to file if requested
    if args.save and not args.reformulate_from_first_set:
        outdir = os.path.join(os.getcwd(), "assets", "cqs")
        jsonld_path = os.path.join(outdir, f"{generation}.jsonld") if not args.reformulate else os.path.join(outdir, f"{generation}_reformulated.jsonld")
        naincludedcqs = cleaned_cqs.copy()

        cleaned_cqs = validate_reformulated(cleaned_cqs)
        cq_to_json_ld(cleaned_cqs, jsonld_path)

        if not args.reformulate:
            cq_to_txt(cleaned_cqs, os.path.join(outdir, f"{generation}.txt"))
        else:
            reform_file = os.path.join(outdir, f"{generation}_reformulated.txt")
            originalcqs = get_cqs_from_file_as_strings(os.path.join(os.getcwd(), "assets", "cqs", "rejected_cqs.json"))
            with open(reform_file, "w", encoding="utf-8") as f:
                f.write("\n---\nOriginal rejected:\n")
                if originalcqs:
                    for q in originalcqs:
                        f.write(q + "\n")
                    f.write("\n---\nReformulated CQs:\n")
                    for q in naincludedcqs:
                        f.write(q + "\n")
        print(f"Saved {len(cleaned_cqs)} CQs to {jsonld_path} and {os.path.join(outdir, f'{generation}.txt')}")

    # -- Dynamically get the source for the CQ
    source_document = get_source_from_arr(source)
    if args.notion:
        jsonld_path = os.path.join(os.getcwd(), "assets", "cqs", f"{generation}.jsonld") if not args.reformulate else os.path.join(os.getcwd(), "assets", "cqs", f"{generation}_reformulated.jsonld")
        competency_questions = get_cqs_from_file(jsonld_path)

        competency_questions = remove_local_ids_from_reformulations(competency_questions) if args.reformulate_from_first_set else None

        notionprompt = "\n".join([
            config['out_examples'],
            config['out_instruction'], 
        ])

        generation_config_UUID = llm_setup_to_notion(
            generation=generation,
            modelname=config["gemini_model"],
            temperature=config["temperature"],
            usage="API",
            llmrole=config["role"],
            prompt=notionprompt,
        )
        notion = get_notion_client()
    
        for cq in tqdm(competency_questions):
            for att in range(3):
                try:
                    write_row(
                        notion,
                        NOTION_DATABASE_ID,
                        "CQ",
                        cq,
                        iteration=currgeneration,
                        generation_config=generation_config_UUID,
                        src_documents=source_document
                    )
                    time.sleep(0.2)
                    break
                except Exception as e:
                    print(f"Timeout at attempt {att}, continuing...")
                    time.sleep(1)

        if args.reformulate:
            for i, reformulated_cq in enumerate(competency_questions):
                if i < len(rejectcqs): 
                    original_hash = rejectcqs[i].get("hash")
                    
                    if original_hash:
                        # Now we can get the page ID since it's been uploaded
                        reformulated_page_id = get_page_id_by_title(reformulated_cq)
                        original_page_id = src_cq_uuid(original_hash)
                        
                        if reformulated_page_id and original_page_id:
                            link_reformulations(reformulated_page_id, original_page_id)
                            print(f"Linked: {reformulated_cq[:50]}...")
                        else:
                            print(f"Could not find page IDs for linking: {reformulated_cq[:50]}...")

        print("Competency questions written to Notion database. Please refresh the page to see the changes.")

    save_llm_insatance(cqset=f"{generation}", isReformulated=reformulated) if args.save else print("LLM instance not saved, as --save argument was not provided.")

if __name__ == "__main__":
    main()