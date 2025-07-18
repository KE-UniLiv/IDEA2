import argparse
import os
import cq_extraction
import notion_utils
import cq_measures
import prompts as p
import utils
import sys
import time

from tqdm import tqdm
from cq_json_ld import cq_to_json_ld
from reformulate_cq import reformulate_cqs, get_rejected_cqs_from_file, store_pulled, validate_reformulated, pull_accepted, pull_rejected
from cq_extraction import get_llm_instance, save_llm_insatance, run_cq_extraction, cq_to_txt, clean_llm_output, configure_prompt, get_generation_number, update_config

#from output_constraints import validate_competency_questions

r"""

CLI interface for running the competency question extraction and storing results in Notion.

Usage:

    Pre-requisites:
        Ensure that all keys are filled in api_config.yml
        Ensure that the TODO requirements are installed (see requirements.txt)

    
    (1): CD into the XAnIML directory:
        cd x:\...\XAnIML

    (2): Run the script with desired arguments:
        python xaniml/runner.py [--model MODEL_NAME] [--temperature TEMPERATURE] [--role ROLE] [--save] [--notion] [--generation GENERATION_LABEL]

    note:
        All of these arguments are optional, and the script will use default values if not provilded.

"""

def main():
    parser = argparse.ArgumentParser(description="Extract and store CQs using LLMs and Notion.")
 
    ## -- Arguments which elicit user input
    parser.add_argument('--model', type=str, default="models/gemini-2.5-flash", help='Model name\n (Options: models/gemini-2.5-flash, models/gemini-2.5-pro, models/gemini-1.5-flash-latest, models/openai-gpt-4)')
    parser.add_argument('--temperature', type=float, default=0.2, help='LLM temperature\n (Options: 0.0 to 1.0) (Default: 0.2)')
    parser.add_argument('--role', type=str, default="SYSTEM_ROLE_A", help='Role for the LLM\n (Options: SYSTEM_ROLE_A, SYSTEM_ROLE_B, SYSTEM_ROLE_C)')
    parser.add_argument('--instruction', type=str, default="CQ_INSTRUCTION_A", help='Instruction for the LLM\n (Options: CQ_INSTRUCTION_A, CQ_INSTRUCTION_B, ' \
    'CQ_INSTRUCTION_C')
    parser.add_argument('--example', type=str, default="CQ_EXAMPLE_A", help='Give examples of CQs for the LLM\n (Options: CQ_EXAMPLE_A, CQ_EXAMPLE_B, CQ_EXAMPLE_C, CQ_ACCEPTED_CQS)')
    parser.add_argument('--generation', type=str, default=None, help='Generation label (auto if not set manually)')

    ## -- Boolean arguments 
    parser.add_argument('--save', action='store_true', help='Save CQs to file (jsonld format)')
    parser.add_argument('--notion', action='store_true', help='Upload CQs to Notion')
    parser.add_argument('--reformulate', action='store_true', help='Reformulate CQs using rejected CQs as input (Note: run with --find_rejected to find rejected CQs first, then run with --reformulate to reformulate them)')
    parser.add_argument('--find_rejected', action='store_true', help='Find rejected CQs in Notion and store (Note: run as the only argument ie python runner.py --find_rejected)')
    parser.add_argument('--find_accepted', action='store_true', help='Find accepted CQs in Notion and store/refresh (Note: Ideally run as the only argument ie python runner.py --find_accepted)')
    #parser.add_argument('--constrain', action='store_true', help='Use output constraints to validate the LLM output (default: False)')
    parser.add_argument('--usage_help', action='store_true', help='Show a more comprehensive help message with usage instructions')
    parser.add_argument('--show_prompt', action='store_true', help='Show the prompts used for CQ extraction and reformulation')
    args = parser.parse_args()

    ## TODO: no default args
    history = utils.load_history_from_file()
    schema_in_history = any(cq_extraction.combined_schemas in h["content"] for h in history)

    if args.usage_help:
        utils.show_customhelp()
        sys.exit(0)

    if args.find_accepted:
        accepted_cqs = pull_accepted()
        store_pulled(accepted_cqs, typeof="accepted")
        sys.exit(0)

    ## -- Find rejected comes first in the hierarchy
    if args.find_rejected:
        rejected_cqs = pull_rejected()
        store_pulled(rejected_cqs, typeof="rejected")
        sys.exit(0) if not args.reformulate else print("Please run with --reformulate and --save to reformulate the rejected CQs and thus save to notion.")


    cqs = ""
    reformulated = False


    ## -- Update config (retain original values if new ones are not provided)
    update_config(
        gemini_model=args.model if args.model else cq_extraction.config["gemini_model"],
        temperature=args.temperature if args.temperature else cq_extraction.config["temperature"],
        role=args.role if args.role else cq_extraction.config["role"],
        out_instruction=args.instruction if args.instruction else cq_extraction.config["out_instruction"],
        out_examples=args.example if args.example else cq_extraction.config["out_examples"],
    )

    ## -- Generation label
    generation = args.generation if args.generation else get_generation_number()

    ## -- Get LLM instance
    model = get_llm_instance(
        cq_extraction.config["gemini_model"],
        api_key=cq_extraction.geminikey,
        role=cq_extraction.config["role"],
        temperature=cq_extraction.config["temperature"]
    )

    if not args.reformulate and not args.find_rejected:

        ## -- Configure and retrieve the prompt for CQ extraction
        prompt = configure_prompt(
            role=cq_extraction.config["role"],
            out_definition=cq_extraction.config["out_definition"],
            out_examples=cq_extraction.config["out_examples"],
            out_instruction=cq_extraction.config["out_instruction"],
            limit=cq_extraction.config["limit"],
            ignore_schemas=True if schema_in_history else False
        )

        formattedprompt ="\n".join([
            cq_extraction.config['role'],
            cq_extraction.config['out_definition'],
            cq_extraction.config['out_examples'],
            cq_extraction.config['out_instruction'],
            cq_extraction.config['limit'],
            cq_extraction.combined_schemas if not schema_in_history else ''
        ])
        
        ## -- Do not redefine
        history.append({"role": "user", "content": formattedprompt}) 

        if history:

            ## -- Convert history to a single prompt string
            prompt_str = "\n".join([h["content"] for h in history])
            cqs = run_cq_extraction(model, prompt=prompt_str)

        else:
            cqs = run_cq_extraction(model, prompt=prompt)

        cleaned_cqs = clean_llm_output(cqs) if cqs else print("No CQs extracted, as no rejected CQs were found. Please run with --find_rejected to find rejected CQs first, then run with --reformulate to reformulate them.")
        
        for q in cleaned_cqs:
            history.append({"role": "assistant", "content": q})

        utils.save_history_to_file(history)

    if args.reformulate:
        update_config(out_instruction="CQ_INSTRUCTION_REFORMULATE")

        reformulated = True

        ## -- Reconfigure the prompt for reformulation with explicit arguments to override default
        cq_extraction.prompt = configure_prompt(
            role=cq_extraction.config["role"],
            out_definition=cq_extraction.config["out_definition"],
            out_examples=cq_extraction.config["out_examples"],
            out_instruction=cq_extraction.config["out_instruction"],
            limit=cq_extraction.config["limit"]
        )

        rejectcqs = get_rejected_cqs_from_file()
        cqs = reformulate_cqs(model, cq_extraction.prompt, rejectcqs)

    cleaned_cqs = clean_llm_output(cqs) if cqs else None

    # -- Similarity and cohesion measures

    generated_cq_embeddings = cq_measures.calculate_embeddings(cleaned_cqs)

    #reference_questions = [line.strip() for line in open("assets/cqs/reference_cqs_1.txt", encoding="utf-8") if line.strip()]
    #reference_cq_embeddings = cq_measures.calculate_embeddings(reference_questions)

    similarity_matrix = cq_measures.calculate_similarity_matrix(generated_cq_embeddings, generated_cq_embeddings)
    print(f"\nCohesion of generated CQs: {cq_measures.calculate_cohesion(similarity_matrix)}")
    print(f"Best matches for generated CQs: {cq_measures.find_best_matches(similarity_matrix, cleaned_cqs, cleaned_cqs)}\n")

    cleaned_cqs = cq_measures.remove_similar_generated(similarity_matrix, cleaned_cqs, threshold=0.95) 

    ## -- Save to file if requested
    if args.save:
        outdir = os.path.join(os.getcwd(), "assets", "cqs")
        jsonld_path = os.path.join(outdir, f"{generation}.jsonld") if not args.reformulate else os.path.join(outdir, f"{generation}_reformulated.jsonld")
        naincludedcqs = cleaned_cqs.copy()

        cleaned_cqs = validate_reformulated(cleaned_cqs) if args.reformulate else cleaned_cqs
        cq_to_json_ld(cleaned_cqs, jsonld_path)
 
        if not args.reformulate:
            cq_to_txt(cleaned_cqs, os.path.join(outdir, f"{generation}.txt"))

        else:

            reform_file = os.path.join(outdir, f"{generation}_reformulated.txt")
            originalcqs = get_rejected_cqs_from_file()
            with open(reform_file, "w", encoding="utf-8") as f:
                f.write("\n---\nOriginal rejected:\n")

                if originalcqs:
                    for q in originalcqs:
                        f.write(q + "\n")

                    f.write("\n---\nReformulated CQs:\n")
                    for q in naincludedcqs:
                        f.write(q + "\n")

        print(f"Saved {len(cleaned_cqs)} CQs to {jsonld_path} and {os.path.join(outdir, f'{generation}.txt')}")

    ## -- Upload to Notion if requested
    if args.notion:
        jsonld_path = os.path.join(os.getcwd(), "assets", "cqs", f"{generation}.jsonld") if not args.reformulate else os.path.join(os.getcwd(), "assets", "cqs", f"{generation}_reformulated.jsonld")
        competency_questions = notion_utils.get_cqs_from_file(jsonld_path)

        notionprompt ="\n".join([
            cq_extraction.config['out_examples'],
            cq_extraction.config['out_instruction'], 
        ])

        generation_config_UUID = notion_utils.llm_setup_to_notion(
            generation=generation,
            modelname=cq_extraction.config["gemini_model"],
            temperature=cq_extraction.config["temperature"],
            usage="API",
            llmrole=cq_extraction.config["role"],
            prompt=notionprompt,
        )
    
        ## -- Avoid API timeouts
        for cq in tqdm(competency_questions):
            for att in range(3):
                try:
                    notion_utils.write_row(
                        cq_extraction.notion,
                        cq_extraction.NOTION_DATABASE_ID,
                        "CQ",
                        cq,
                        generation_config=generation_config_UUID
                    )
                    time.sleep(0.2)
                    break
                except Exception as e:
                    print(f"Timeout at attempt {att}, continuing...")
    

        print("Competency questions written to Notion database. Please refresh the page to see the changes.")

    print(prompt) if args.show_prompt else None

    ## -- Optionally save LLM instance
    save_llm_insatance(cqset=f"{generation}", isReformulated=reformulated) if args.save else print("LLM instance not saved, as --save argument was not provided.")

if __name__ == "__main__":
    main()