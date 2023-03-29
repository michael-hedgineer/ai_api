import os
import json
import sys
import openai
from loguru import logger

from typing import Callable, Any
from pydantic import BaseModel



class ApiSpec(BaseModel):
    '''
    The API specification for exposing the API to the generaive AI
    '''

    name: str
    description: str
    args: list
    code_example: str
    results_description: str
    example_results: list
    example_query: list
    example_response: list
    example_kwargs: list

    def verify_dict(spec: dict) -> bool:
        '''
        Verifies if a spec dictionary is valid with required arguments, all in the correct type. If error
        raises an Assertion Error
        '''

        assert 'name' in spec, 'Missing the name in the the api spec'
        required_args = [
            'name', 
            'description', 
            'args', 
            'code_example', 
            'results_description',
            'example_results',
            'example_query',
            'example_response',
            'example_kwargs'
        ]

        for i in required_args:
            assert i in spec, f"Missing the {i} value for the api spec for {spec['name']}"

        assert type(spec['args']) == list, f"Spec args be a list for the {spec['name']} API"

        example_keys = ('example_results', 'example_query', 'example_response', 'example_kwargs')
        
        for _example in example_keys:
            assert type(spec[_example]) == list, \
            f'{_example} must be a list'
        
        example_len = None
        for _example in example_keys:
            if example_len is None:
                example_len = len(spec[_example])
            else:
                assert len(spec[_example]) == example_len, \
                'Example Results, Query, Response, and Kwargs but all be the same length'

        assert len(set(map(len, (spec[i] for i in example_keys)))) == 1, \
            'Example Results, Example Query, and Example Response must all be equal length'

        for arg in spec['args']:
            assert type(arg) == str or type(arg) in (list, tuple) and len(arg) == 3, \
            f"Arg value in spec must be a list of len == 4 (name, type, desc)"
        
        assert len(spec['example_results']) > 0, \
            "There must be at least 1 set of Example Resuls, Query and Response"
        
        for kwarg in spec['example_kwargs']:
            assert isinstance(kwarg, dict)

        return True
    
class AiApi():

    def __init__(self, model="gpt-3.5-turbo", openai_api_key="", api_temperature=0, answer_temperature=.3, LOG_LEVEL="INFO"):

        logger.add(sys.stderr, format="{time} {level} {message}", level=LOG_LEVEL, backtrace=True, diagnose=True)
        
        if not openai_api_key:
            openai_api_key = os.environ.get('OPENAI_API_KEY')
        
        openai.api_key = openai_api_key

        self.model = model
        self.api_temperature = api_temperature
        self.answer_temperature = answer_temperature
        self._apis = {}

        self._api_prompts = []
        self.template_prompt_api_identify = 'Identify what APIs with corresponding arguments need to be called to answer this query: "{0}"'

        pass


    def register_api(self, use_doc_str:bool=True, **kwargs):
        """
        Register Function for being accessble to the the LLL Model

        Args:
            name (str): The unique name for the function
            use_doc_str (bool): Use the docstring of the function for the AI Documentation

            Optional additioonal arguments for the ApiSpecifictions:
            api_dict (dict): Dictionary for the JSON Spec
            api_spec (ai_api.ApiSpec): The ApiSpec object
            json_spec (str): Location of the JSON spec for the API
            yaml_spec (str): Location of the yaml spec for the API
        """
        
        spec = None
        if api_dict := kwargs.get('api_dict'):
            ApiSpec.verify_dict(api_dict)
            spec = ApiSpec(**api_dict)
        elif api_spec := kwargs.get('api_spec'):
            assert isinstance(api_spec, ApiSpec), \
                "api_spec value must be an ApiSpec instance when registering API."
            ApiSpec.verify_dict(dict(api_spec))
            spec = api_spec
       
        def registered_function(func):

            def wrapped_func(*args, **kwargs):
                
                return func(*args, **kwargs)
            
            api = Api(function=func, spec=spec, use_doc_str=use_doc_str)
            self._apis[func.__name__] = api

            return wrapped_func
        
        return registered_function
        
    def _set_apis_prompt(self) -> str :
        """Generates a list of prompts that guide the AI to identify the APIs to be called.

        The method sets self.api_prompts based on a a system prompt and an example prompt that 
        provides instructions to the LLM for identifying APIs and their arguments. Included in this is documenation 
        for each API and with example arguments to be passed to the AI assistant. 
        The prompts are generated in JSON format and include examples for each API.

        Returns:
            str: A list of prompts that guide the user to identify the APIs to be called.

        Raises:
            None
        """
            
        api_list="\n".join(self._apis.keys()),
        api_documentation="\n".join([i.formatted_documentation for i in self._apis.values()])

        prompts = []
        system_prompt = f"""
        Your job is to identify APIs that need to be called to answer a user query.
        You MUST ONLY reply in JSON format. DO not include additional text in your reply.
        You will be given a list of APIs to choose from any you must identify what APIs you need to call and what arguments to pass to them.
        You ONLY reply with JSON formatted text that includes the API name and the kwargs to pass to it. Below is an example:

        Example:
        {{
            "apis": [
                {{"name": "api_name", "kwargs": {{"arg1": "value1", "arg2": "value2"}}
            ],
            "notes": "Additional notes go here if needed"
        }}

        List of APIs:
        {api_list}

        Documentation for each API are as follows:
        
        {api_documentation}
        """.replace('        ', '')

        prompts.append({'role': 'system', 'content': system_prompt})  
                
        self._api_prompts = prompts

    def _generate_answer_prompts(self, apis_used: list) -> list:
        '''
        Generates the prompts that describe the APIs used along with examples in the JSON
        format that the AI should expect the data in.

        Args:
            apis_used (list): A subset of the APIs that were used in this query

        Returns:
            list of prompts including the system and a 1 shot example
        '''
        
        api_documentation = "\n".join(self._apis[i].formatted_documentation for i in apis_used)

        prompts = []
        system_prompt = f"""
        You are an assistant that answers a user query using supplemenal API informatin.
        Results include the api used, the arguments passed to it, and the results of the call.
        Answer the question as best you can with this information.
        DO NOT reference the APIs that were used in the response.

        Below is a description of the APIs used and how to interpret their results:
        {api_documentation}
        """.replace('        ', '')

        prompts.append({'role': 'system', 'content': system_prompt})
            
        return prompts
    

    def identify_apis(self, query: str) -> dict:
        '''
        Identifies the APIs that need to be called to answer the query

        Args:
            query (str): The query to be answered

        Returns:
            dict: The APIs that need to be called and their arguments
        '''
        
        if not self._api_prompts:
            self._set_apis_prompt()

        query_prompt = [{
            'role': 'user',
            'content': self.template_prompt_api_identify.format(query)
            }
        ]
        
        for i in (self._api_prompts + query_prompt):
            logger.debug(i['content'])

        api_response = openai.ChatCompletion.create(
            model=self.model,
            messages=(self._api_prompts + query_prompt),
            temperature=self.api_temperature
        )

        api_json_text = api_response.choices[0]['message']['content']
        
        try:
            logger.debug(api_json_text)
            api_calls = json.loads(api_json_text)
        except json.decoder.JSONDecodeError:
            logger.exception("Error decoding JSON")
            raise

        return api_calls
    

    def answer_query(self, api_results: dict) -> str:
        '''
        Answers the query based on the APIs that were called

        Args:
            api_calls (dict): The APIs that need to be called and their arguments

        Returns:
            str: The response to the query
        '''

        apis_used = set(x for x in (i['name'] for i in api_results['apis']))
        answer_prompts = self._generate_answer_prompts(apis_used)

        answer_prompt = [{
            'role': 'user',
            'content': json.dumps(api_results)
        }]
        
        for i in (answer_prompts + answer_prompt):
            logger.debug(i['content'])
        
        try:
            answer_response = openai.ChatCompletion.create(
                model=self.model,
                messages=(answer_prompts + answer_prompt),
                temperature=self.answer_temperature
            )

            answer_text = answer_response.choices[0]['message']['content']
        except Exception:
            logger.exception("Error answering query")
            raise

        return answer_text


    def run_function(self, function: Callable, kwargs: dict) -> Any:
        '''
        Runs a function with the given kwargs

        Args:
            function (Callable): The function to be run
            kwargs (dict): The arguments to be passed to the function

        Returns:
            Any: The result of the function
        '''

        return function(**kwargs)
    

    def execute_query(self, query:str) -> str:
        '''
        Orchestrates the entire query process below:
        1. Use AI to identify what APIs need to be called
        2. Executing the functions with the corresponding arguments
        3. Pass back the results to the AI to execute
        '''

        api_calls = self.identify_apis(query)

        api_results = []
        for api_dict in api_calls['apis']:

            api = self._apis[api_dict['name']]

            result = self.run_function(api.function, api_dict['kwargs'])

            api_results.append({
                'name': api_dict['name'],
                'kwargs': api_dict['kwargs'],
                'result': result
            })
        
        query_and_api_results = {'user_request': query, 'apis': api_results}

        answer = self.answer_query(query_and_api_results)
        return answer
 
                
class Api():
    '''
    Wrapper around a registered api that contains the formatted prompts, the callable function,
    and other meta data used to reference this API
    '''

    name: str
    function: Callable
    spec: ApiSpec
    formatted_spec_doc: str

    def __init__(self, function: Callable, use_doc_str: bool, spec: ApiSpec):
        self.spec = spec
        self.name = function.__name__
        self.function = function
        self.formatted_documentation = self._create_api_documentation(self.spec)

    def _create_api_documentation(self, spec: dict, use_doc_str=True) -> str:
        '''
        Create the documentation string for each API from the spec given. This is then
        injected into the api and answer prompts to inform the AI how to use the API
        '''

        template = f'''
        Python Function Name: {self.function.__name__}
        Python Documentation:
        {self.function.__doc__}
        '''

        return template