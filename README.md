# IDEA2
Expert-in-the-loop requirement elicitation and analysis for ontology engineering

IDEA2 is a framework which defines workflows for enriching ontology engineering by leveraging state-of-the-art Large Language Models (LLMs) such as `Gemini` and `OpenAI`, and advancements in the fields of Knowledge Engineering and Ontology Engineering. It provides a system through which users can utilise LLMs to inform the creation and refinement of Ontologies through Competency Questions (CQs). With this framework, the user can select a model, hyperparameters and prompt configurations to extract competency questions for schemas, and populate a notion page with the results alongisde the associated provenance.

# Overview

## Prepare data 📝

To start using IDEA2, the following must be provided in the appropriate area in [`api_config.yml`](idea2/api_config.yml):

- Gemini API key
- OpenAI API
- Notion Integration Key
- Notion Page Key
- Notion Database key (CQ Pool)
- Notion LLM Database Key (LLM configurations and provenance)

Furthermore, schemas should be defined in [`assets/schema`](assets/schema).

## Schemas 📜

Schemas are used to inform the creation of the ontology due to the fact that the ontology should be able to answer the (verified) CQs. An example of schemas is the [AnIML Schemas](https://www.animl.org/) which contains both a technique schema and a core schema. Given these two schemas as part of a prompt, the LLM will extract CQs relevant to the schema which can be used to inform the creation of an ontology or to see if a former ontology can answer certain CQs. The schema is used in tandem with the prompt to attain powerful results for Ontology Engineering.

## LLMs and Hyperparameters 🤖

Both `Gemini` and TODO `OpenAI` are supported for the extraction of competency questions. the Temperature hyperparameter can be given to the model which expresses how creative the LLM is allowed to be in its response. Please ensure that you have access to the model you require through your API key, or you may recieve errors.

TODO: List caveats and errors if any

## Prompts 🗣️

Prompt engineering is at the core of this workflow and [`prompts.py`](idea2/prompts.py) defines the prompts that can be given to the model, typically we have:

- A role for the LLM to take (Requirements engineer, Ontology creator, Ontology tester)

- Examples of CQs for other domains (Music meta etc)

- Instructions for the LLM (Extract all / assume ontology exists / reformulate CQs)

Reformulation of a CQ takes place when any given CQ has a score of <0 on the notion database. If this occurs, --find_rejected will pull these and store them in [`rejected_cqs.json`](assets/cqs/rejected_cqs.json) and --reformulate will allow the reformulation of those rejected CQs.

## Notion 💾

The framework contains notion intgeration which allows for domain experts to reject generated CQs. These rejected CQs are then fed back into the LLM, reformulated, and sent back to the notion database. 

All in all, the notion integration allows for:

- Saving of LLM instances (provenance) for a set of CQs
- Saving of extracted or reformulated CQs
- Reformulation of CQs

## Usage

When all the data is in place:

- Open a terminal and cd to your local instance of the source (e.g `C:/GitHub/IDEA2`)
- Run `python idea2/runner.py <arg1> <arg2> ... <arg n>`

Below are the supported arguments, please run `python idea2/runner.py --usage_help` if the default help given is not useful for you.

```
usage: runner.py [-h] [--model MODEL] [--temperature TEMPERATURE] [--role ROLE] [--instruction INSTRUCTION]
                 [--example EXAMPLE] [--generation GENERATION] [--save] [--limit] [--notion] [--reformulate]
                 [--find_rejected] [--find_accepted] [--constrain] [--usage_help] [--show_prompt]

Extract and store CQs using LLMs and Notion.

options:
  -h, --help            show this help message and exit
  --model MODEL         Model name (Options: models/gemini-2.5-flash, models/gemini-2.5-pro, models/gemini-1.5-flash-
                        latest, models/openai-gpt-4)
  --temperature TEMPERATURE
                        LLM temperature (Options: 0.0 to 1.0) (Default: 0.2)
  --role ROLE           Role for the LLM (Options: SYSTEM_ROLE_A, SYSTEM_ROLE_B, SYSTEM_ROLE_C)
  --instruction INSTRUCTION
                        Instruction for the LLM (Options: CQ_INSTRUCTION_A, CQ_INSTRUCTION_B, CQ_INSTRUCTION_C)
  --example EXAMPLE     Give examples of CQs for the LLM (Options: CQ_EXAMPLE_A, CQ_EXAMPLE_B, CQ_EXAMPLE_C,
                        CQ_ACCEPTED_CQS)
  --generation GENERATION
                        Generation label (auto if not set manually)
  --save                Save CQs to file (jsonld format)
  --limit               Limit the number of CQs extracted (default: False) (note: must be called with --instruction)
  --notion              Upload CQs to Notion
  --reformulate         Reformulate CQs using rejected CQs as input (Note: run with --find_rejected to find rejected
                        CQs first, then run with --reformulate to reformulate them)
  --find_rejected       Find rejected CQs in Notion and store (Note: run as the only argument ie python runner.py
                        --find_rejected)
  --find_accepted       Find accepted CQs in Notion and store/refresh (Note: Ideally run as the only argument ie
                        python runner.py --find_accepted)
  --constrain           Use output constraints to validate the LLM output (default: False)
  --usage_help          Show a more comprehensive help message with usage instructions
  --show_prompt         Show the prompts used for CQ extraction and reformulation

```