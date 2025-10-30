import notion_metrics
import notion_utils
"""
A collection of modular components for generating prompts for schema2cq.
"""

OENG_ROLE = """
You are an ontology engineer working on a project to develop a new ontology
for a domain of interest. You have been tasked with developing the ontology
and ensuring that it is aligned with the requirements of the domain experts. 
"""

SYSTEM_ROLE_A = OENG_ROLE + "You will focus on requirement engineering."

SYSTEM_ROLE_B = OENG_ROLE + "You will focus on ontology creation."

SYSTEM_ROLE_C = OENG_ROLE + "You will focus on ontology testing."

# *****************************************************************************
# COMPETENCY QUESTIONS DEFINITION AND EXAMPLES
#  - CQ_EXAMPLE_A: CQ examples from the Music Meta ontology
#  - CQ_EXAMPLE_B: CQ examples from the Music Annotation pattern
#  - CQ_EXAMPLE_C: CQ examples from the Software Ontology
# *****************************************************************************

CQ_DEFINITION_A = """
A competency question (CQ) is a question that can be answered using the
knowledge represented in an ontology. Competency questions are used in
requirement engineering to determine the scope and coverage of an ontology and
to evaluate its effectiveness. Competency questions are typically formulated in
natural language and are used to test the ontology's ability to provide answers
to specific queries. Competency questions are an important part of the ontology
development process as they help to ensure that the ontology is fit for purpose
and meets the needs of its users.
"""

N = notion_metrics.getn()

CQ_EVALUATION_DEFINITION = f"""
The reformulated CQs you generated in iteration {notion_utils.get_current_iteration_from_dashboard()} were passed to N={N} domain experts for evaluation. 
The score of a CQ is based on a simple majority vote, with any CQ that has a score of less than 0 needing reformulation. 
For example, if a CQ has a score of -3 and has been voted by 3 experts (out of N=4), then all the active participants downvoted that CQ.
"""

CQ_EVALUATION_DEFINITION_BME = f"""
The set of CQs given include both the accepted and rejected CQs from the previous iteration.
All CQs were passed to N=3 domain experts for evaluation.
The score of a CQ is based on a simple majority vote, with any CQ that has a score of less than or equal 0 needing reformulation.
For example, if a CQ has a score of -2 and has been voted by 2 experts (out of N=3), then all the active participants downvoted that CQ.
Otherwise, if a CQ has a score of 1 or more, then it has been accepted by the majority of the experts as a good CQ.
"""

CQ_ACCEPTED = f"""
You can assume that all the CQs from the previous iteration that are not included below successfully passed the validation stage 
(they were accepted by majority). 
Consider these as good CQs.
"""

CQ_EXAMPLE_A = """
Examples of competency questions for an ontology about music metadata include:
Which is the composer of a musical piece?
Is the composer of a musical piece known?
Which are the members of a music ensemble?
Which role a music artist played within a music ensemble?
In which time interval has a music artist been a member of a music ensemble?
Where was a music ensemble formed?
Which award was a music artist nominated for?
Which award was received by a music artist?
Which music artists has a music artist been influenced by?
Which music artist has a music artist collaborated with?
Which is the start date of the activity of a music artist?
Which is the end date of the activity of a music artist?
Which is the name of a music artist?
Which is the alias of a music artist?
Which is the language of the name/alias of a music artist?
Which music dataset has a music algorithm been trained on?
Which is the process that led to the creation of a musical piece?
In which time interval did the creation process took place?
Where did the creation process took place?
Which are the creative actions composing the creation process of a musical piece?
Which task was executed by a creative action?
Which are the parts of a musical piece?
Which collection is a musical piece member of?
Where was a musical piece performed?
When was a musical piece performed?
Which music artists took part to a musical performance?
Which is the recording process that recorded a musical performance?
Which is the recording produced by a recording process?
"""

CQ_EXAMPLE_B = """
Examples of competency questions for an ontology about music annotation include:
- What is the type of an annotation/observation for a musical object?
- What is the time frame within the musical object addressed by an annotation?
- What is its start time (i.e. the starting time of the time frame)?
- Which are the observations included in an annotation?
- For a specific observation, what is the starting point of its addressed time frame, within its reference musical object?
- For a specific observation, what is its addressed time frame, within the musical object?
- What is the value of an observation?
- Who/what is the annotator of an annotation/observation, and what is its type?
- What is the confidence of an observation?
- What is the musical object addressed by an annotation?
"""

CQ_EXAMPLE_C = """
What is the algorithm used to process this type of data?
What are the alternatives to this software?
Are there any other alternatives to this software?
Which of the named and published algorithms does this tool use?
Are there any modifications to the algorithm this tool uses?
Does this software provide XML editing capabilities?
What type of software is this?
What software can perform this task?
Is this software appropriate for my task?
What are the primary inputs and outputs of this software?
What visualization software is available for this type of data, and what does it cost?
What software works best with my dataset?
Does this software render GIFs?
What software tool can create this type of data?
What software can I use with my data to support my task?
What are the input and output formats for this software?
What data can be analyzed with this tool and version?
What software can read a .cel file?
What are the export options for this software?
What is the valid input for this software?
Can this software export from its proprietary data format to an open format such as CSV or TXT?
Can software A work with data that is output from software B?
To what extent does this software support appropriate open standards?
Is this software compatible with this other software?
What open-source, maintained software can I use to process these files in this format?
Is the output format of this software proprietary?
Can I still use this software if the supplier goes out of business?
Given this input, what are the data exports for this version of the software?
Where can I get this software?
Is there a mailing list for this software?
How do I get help with this software?
How can I get problems with this software fixed?
Are there any active forums discussing this software's use?
Where do I get updates for this software?
Who developed this software?
What is the homepage of this software?
Can we collaborate with the developers of this software?
Where can I buy this software from?
Where can I download this software?
What is the fastest software to read this type of data?
Does this software meet the ISO-4 standard?
Do I know anyone who has used this software or processed this type of data?
How and where has this software been used successfully in the past?
How long has this software been around?
How actively developed is this software?
What do others say about the quality of this software?
How reliable is this software?
What software is better for this task given these restrictions?
Who are the potential users of this software we are developing?
How popular is this software?
Who else has used this tool today?
How popular is this software?
How many settings do I need to know to rerun this analysis?
Is this software available as a web service?
What is the version of this software?
What new features are in this version of this software?
What are the differences between versions of this software?
When was the 1.0 version of this software released?
Is this software open source? Is there a community developing it?
What license does this software have, and how permissive is it?
Is this software open source or not?
When did the license type of this software change?
Who owns the copyright for this software?
What is the licensing history of this software?
How many licenses do we need to run this software productively?
Is this software FOSS (Free and Open Source Software)?
Do I need a password to use this software?
Is this software free or not?
What level of expertise is required to use this software?
Are there any usage examples for this software?
Is there any documentation for this software, and where can I find it?
Does this software have a tutorial?
Where is the documentation for this software?
How well documented is this software for developers?
How do I cite this software?
Is there a publication associated with this software?
Is this software scriptable?
Is this software extensible?
How can I extend this software to include a new function?
Can I use some components of this software for my own software?
What hardware do I need to run this software?
What graphics card does this software require?
In what language was this software implemented?
What platform does this software run on?
Can I install this software on a university computer?
What compiler do I need to compile source code on this platform?
Does this software work on 64-bit Windows?
Do I need a license key to use this software?
"""

# *****************************************************************************
# COMPETENCY QUESTIONS INSTRUCTIONS for EXTRACTION
# *****************************************************************************

CQ_INSTRUCTION_A = """
Given the schema definition, extract all the related competency questions. 
For each competency question, make sure it expresses a requirement that is supported or addressed by the schema.
Do not repeat any competency questions that have already been generated in previous responses or are present in the chat history.
"""

CQ_INSTRUCTION_B = """
Given the schema definition below, extract all the competency questions that
can be answered as if the corresponding ontology was already implemented.
For each competency question, make sure it expresses a requirement that is supported or addressed by the schema.
Do not repeat any competency questions that have already been generated in previous responses or are present in the chat history.
"""

CQ_INSTRUCTION_C = """
Given the schema definition below, extract all the competency questions to
inform the development of an ontology to represent the knowledge in the schema. 
For each competency question, make sure it expresses a requirement that is supported or addressed by the schema.
Do not repeat any competency questions that have already been generated in previous responses or are present in the chat history.
"""

CQ_INSTRUCTION_REFORMULATE = """
You will now receive the set of rejected CQs with their votes, (negative) score, and any commented feedback, when available. 
Your task is to reformulate these CQs by using the feedback from the validators and the schema definitions you were originally given. 
Do not mark a reformulated competency question as "Reformulated" or "Reformulated CQ", only provide the reformulated competency question. 
Only reformulate the rejected competency questions, do not extract new competency questions.
"""

## -- Injection into iteration 2 with no prior extraction or knowledge.
## -- ID
CQ_INSTRUCTION_REFORMULATE_INJECTION_USER_STORY = """
You will now receive the definition of the user stories, and personas in markdown format.
After this, you will receive the entire set of CQs with their votes, score, and any commented feedback, when available.
A CQ is considered rejected if it has a score of less than or equal to 0. All other CQs are considered accepted.
Your task is to reformulate all of the CQs that have a score of less than or equal to 0 by using the feedback from the validators and both the user story and personas you were given.
Provide the ID of the rejected CQ from which you are reformulating, along with the reformulation itself.
Do not mark a reformulated competency question as "Reformulated" or "Reformulated CQ", only provide the reformulated competency question. 
Only reformulate the rejected competency questions, do not extract new competency questions.
"""