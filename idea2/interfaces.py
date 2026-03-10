"""
This module provides an abstract interface to prompt a general LLM, as well as
concrete implementations for a range of proprietary and open source models.
"""
import copy
import logging

from typing import List

logger = logging.getLogger(__name__)

# Lazy imports for slow libraries
_genai = None
_OpenAI = None

def _get_genai():
    """Lazy import of google.generativeai"""
    global _genai
    if _genai is None:
        import google.generativeai as genai
        _genai = genai
    return _genai

def _get_openai():
    """Lazy import of OpenAI"""
    global _OpenAI
    if _OpenAI is None:
        from openai import OpenAI
        _OpenAI = OpenAI
    return _OpenAI


class LLM:
    """
    Abstract interface for a language model.
    """

    def __init__(self,
                 model=None,
                 model_path=None,
                 api_key=None,
                 role=None,
                 **kwargs):
        """
        Initialise the language model and the open the session.
        
        Parameters
        ----------
        model : str
            The name of the language model.
        model_path : str
            The path to the language model.
        api_key : str
            The API key for the language model.
        role : str
            The role of the language model.
    
        """     
        raise NotImplementedError

    def generate(self, prompt, max_tokens=None, temperature=None, top_p=None):
        """
        Generate content from the language model.

        Parameters
        ----------
        prompt : str
            The prompt for the language model.
        max_tokens : int
            The maximum number of tokens to generate.
        temperature : float
            The temperature of the generation.
        top_p : float
            The top p value of the generation.
        """
        raise NotImplementedError


class GeminiLLM(LLM):
    """
    Concrete implementation of the LLM interface for a Gemini model.
    """

    def __init__(self,
                 model=None,
                 model_path=None,
                 api_key=None,
                 role=None,
                 **kwargs):
        """
        Initialise the Gemini language model and open the session.
        
        Parameters
        ----------
        model : str
            The name of the language model, for example, 
            `model=models/gemini-1.5-flash-latest`.
        model_path : str
            The path to the language model.
        api_key : str
            The API key for the language model.
        role : str
            The role of the language model.

        Examples of generation_config that can be passed to kwargs:
        `generation_config = {"response_mime_type": "application/json"}`
        """
        if model_path is not None:
            raise ValueError("Model path is not supported for Gemini models.")
        genai = _get_genai()
        genai.configure(api_key=api_key)
        if "generation_config" in kwargs:
            generation_config = kwargs.get("generation_config", {})
        else:  # default generation config
            generation_config = genai.GenerationConfig(
                max_output_tokens=kwargs.get("max_tokens", None),
                temperature=kwargs.get("temperature", None),
                top_p=kwargs.get("top_p", None),
        )
        # Get the model basic info
        model_info = genai.get_model(model)
        print(f"{model} - input limit: {model_info.input_token_limit},"\
              f" output limit: {model_info.output_token_limit}")
        # Load and initialise the model
        self.model = genai.GenerativeModel(
            model_name=model,
            system_instruction=role,
            generation_config=generation_config,
        )
        logger.info(f"Model {model} loaded successfully.")
        self.llm_params = kwargs

    @staticmethod
    def get_models(detailed=False):
        """
        Get the available models for the language model.
        """
        genai = _get_genai()
        info = lambda m : m if detailed else m.name
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods:
                print(info(m))  # print the name of the model

    def _build_generation_config(self, **kwargs):
        """
        Build the generation config for the language model, using the input
        parameters, and setting them to the current values if not provided.
        """
        genai = _get_genai()
        config_valid_attrs = [attr for attr in dir(genai.GenerationConfig)
                              if not attr.startswith("__")]
        #Get the current generation config to keep the unchanged values
        new_config = copy.deepcopy(self.model._generation_config)
        for key, value in kwargs.items():
            if key not in config_valid_attrs:  # check if the param is valid
                raise ValueError(f"Invalid param {key} for GenerationConfig.")
            if value is not None:  # keep current value if available
                new_config[key] = value
        new_config = genai.GenerationConfig(**new_config)
        return new_config

    def generate(self, prompt, max_tokens=None, temperature=None, top_p=None):
        """
        Generate text given a prompt using the Gemini language model.

        Parameters
        ----------
        prompt : str
            The prompt for the language model.
        max_tokens : int
            The maximum number of tokens to generate.
        temperature : float
            The temperature of the generation.
        top_p : float
            The top p value of the generation.
        """
        print(f"Tokens for prompt: {self.model.count_tokens(prompt)}")
        # Build the generation config from the input parameters
        generation_config = self._build_generation_config(
            max_output_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,

            # For structured output
            response_mime_type="application/json",
            response_schema=list[str]
        )
        # chat = model.start_chat(history=[])
        raw_response = self.model.generate_content(
            prompt, generation_config=generation_config)
        # response = json.loads(raw_response.text)
        return raw_response.text


class OpenAILLM(LLM):
    """
    Concrete implementation of the LLM interface for an OpenAI model.
    """

    def __init__(self,
                 model=None,
                 model_path=None,
                 api_key=None,
                 role=None,
                 **kwargs):
        """
        Initialise the OpenAI language model and open the session.
        
        Parameters
        ----------
        model : str
            The name of the language model.
        model_path : str
            The path to the language model.
        api_key : str
            The API key for the language model.
        role : str
            The role of the language model.
        """
        if model_path is not None:
            raise ValueError("Model path is not supported for OpenAI models.")
        OpenAI = _get_openai()
        self.client = OpenAI(api_key=api_key)
        self.role = role
        self.model = model

    def get_models(self, detailed=False):
        """
        Get the list of model names available through the OpenAI API.
        """
        models = self.client.models.list()
        return [m.id for m in models.data] if detailed else models.data

    def generate(self, prompt, max_tokens=None, temperature=None, top_p=None):
        """
        Generate content from the language model.

        Parameters
        ----------
        prompt : str
            The prompt for the language model.
        max_tokens : int
            The maximum number of tokens to generate.
        temperature : float
            The temperature of the generation.
        top_p : float
            The top p value of the generation.
        
        Other parameters not yet implemented
        -------------------------------------
        - frequency_penalty
        - presence_penalty
        - logit_bias
        - m (choices)
        - response_format
        - stop
        """        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.role},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            seed=None,  # FIXME: not implemented
            # response_format=Class,
        )
        return response.choices[0].message.content
