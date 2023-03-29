import os
import json
import openai

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

    def __init__(self, model="gpt-3.5-turbo", open_api_key="", api_temperature=0, answer_temperature=.3):

        if not open_api_key:
            open_api_key = os.environ.get('OPENAI_API_KEY')
        
        openai.api_key = open_api_key
        
        self.model = model
        self.api_temperature = api_temperature
        self.answer_temperature = answer_temperature
        self._apis = {}

        self._api_prompts = []
        self.template_prompt_api_identify = 'Identify what APIs need to be called in this query: "{0}"'

        pass


    def register_api(self, name:str, *args, **kwargs):
        """
        Register Function for being accessble to the the LLL Model

        Args:
            name (str): The unique name for the function
            use_doc_str (bool): Use the docstring of the function

            One of below for the spec:
            api_dict (dict): Dictionary for the JSON Spec
            api_spec (ai_api.ApiSpec): The ApiSpec object
            json_spec (str): Location of the JSON spec for the API
            yaml_spec (str): Location of the yaml spec for the API
        """
        
        if api_dict := kwargs.get('api_dict'):
            ApiSpec.verify_dict(api_dict)
            spec = ApiSpec(**api_dict)
        elif api_spec := kwargs.get('api_spec'):
            assert isinstance(api_spec, ApiSpec), \
                "api_spec value must be an ApiSpec instance when registering API."
            ApiSpec.verify_dict(dict(api_spec))
            spec = api_spec
        else:
            raise NotImplementedError('Only the api_spec or api_dict argument is implemented')

        assert name == spec.name, 'The name of the registered function and the spec do not match'
        
        def registered_function(func):

            def wrapped_func(*args, **kwargs):
                
                return func(*args, **kwargs)
            
            api = Api(function=wrapped_func, spec=spec)
            self._apis[name.lower()] = api

            return wrapped_func
        
        return registered_function
        
    def _set_apis_prompt(self) -> str :
        """Generates a list of prompts that guide the API to identify the APIs to be called.

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
        You are the first stage in a framework that helps users interact with generative AI.
        Your job is to identify what APIs need to be called in order to help a second AI assistant answer a user request.
        You only reply in JSON format.
        You must identify what APIs need to be called AND what their arguments are.

        There are {len(self._apis)} APIs to choose from that are listed below:

        {api_list}

        Documentation for each API are as follows:
        
        {api_documentation}
        """.replace('        ', '')

        prompts.append({'role': 'system', 'content': system_prompt})

        # Add in all of the examples for N-Shot tests
        for name, api in self._apis.items():
            for i_example in range(len(api.spec.example_results)):
                prompts.append({
                    'role': 'user',
                    'content': self.template_prompt_api_identify.format(
                        api.formatted_spec['example_results']
                    )
                })
                prompts.append({
                    'role': 'assistant',
                    'content': json.dumps(
                        {"apis": [
                            {
                                'name': api.spec.name,
                                'kwargs': api.spec.example_kwargs
                            }
                        ]}
                    )
                })   
                
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
        You are the last step in a framework that helps users interact with generative AI.
        Before you recieved each user request, another AI identified which APIs needed to be called to answer this request and added the resuls to this response.
        The user request is listed below along with the results of the API calls.

        Your job is to:
        1. Understand the user query
        2. Understand the API results that were made and why
        3. Answer with the best response to the user query by using the api results as though you are a research assistant

        Below is the list of the {len(apis_used)} API calls that are used:

        {api_documentation}

        """.replace('        ', '')

        prompts.append({'role': 'system', 'content': system_prompt})

        for name in apis_used:
            api = self._apis[name]
            for i_example in range(len(api.spec.example_results)):
                example_dict = {
                    "user_request": api.spec.example_query[i_example],
                    "apis": [
                        {   
                            "name": name,
                            "kwargs": api.spec.example_kwargs[i_example],
                            "result": api.spec.example_results[i_example]
                        }
                    ]
                }

                prompts.append({'role': 'user', 'content': json.dumps(example_dict, indent=4)})
                prompts.append({'role': 'assistant', 'content': self._apis[name].spec.example_response[0]})
            
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
        
        api_response = openai.ChatCompletion.create(
            model=self.model,
            messages=(self._api_prompts + query_prompt),
            temperature=self.api_temperature
        )

        api_json_text = api_response.choices[0]['message']['content']
        
        try:
            api_calls = json.loads(api_json_text)
        except json.decoder.JSONDecodeError:
            print(api_json_text)
            raise

        return api_calls
    

    def answer_query(self, query: str, api_results: dict) -> str:
        '''
        Answers the query based on the APIs that were called

        Args:
            query (str): The query to be answered
            api_calls (dict): The APIs that need to be called and their arguments

        Returns:
            str: The response to the query
        '''

        apis_used = set(x for x in (i['name'] for i in api_results['apis']))
        answer_prompts = self._generate_answer_prompts(apis_used)

        answer_prompt = [{
            'role': 'user',
            'content': {
                "user_request": query,
                "apis": api_results
            }
        }]
        
        answer_response = openai.ChatCompletion.create(
            model=self.model,
            messages=(answer_prompts + answer_prompt),
            temperature=self.answer_temperature
        )

        answer_text = answer_response.choices[0]['message']['content']

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

        answer = self.answer_query(query, {'user_request': query, 'apis': api_results})
        return answer
 
                
class Api():
    '''
    Wrapper around a registered api that contains the formatted prompts, the callable function,
    and other meta data used to reference this API
    '''

    name: str
    function: Callable
    spec: ApiSpec
    formatted_spec: dict
    formatted_spec_doc: str

    def __init__(self, function: Callable, spec: ApiSpec):
        self.spec = spec
        self.name = spec.name 
        self.function = function
        self.formatted_spec = self._create_formatted_spec(spec)
        self.formatted_documentation = self._create_api_documentation(self.formatted_spec)


    def _create_formatted_spec(self, spec) -> dict:
        '''
        Formats all of the values in the spec so they can be referenced in the 
        ai prompts
        '''

        formatted_spec = {}
        # The formatting function for any special string formatting for arguments
        format_dict = {
            'args': self._format_args,
            'example_results': self._format_examples,
            'example_query': self._format_examples,
            'example_response': self._format_examples,
            'example_kwargs': lambda x: x
        }

        for k, v in dict(spec).items():
            format_func = format_dict.get(k, self._format_default)
            formatted_spec[k] = format_func(v)
        
        return formatted_spec

    def _format_default(self, value):
        '''
        The default value formatter for a spec value
        '''

        if not isinstance(value, str):
            return str(value).strip()
        
        return value.strip()

    def _format_args(self, args: list) -> str:
        '''
        Formats the function arguments as a string for the AI using standard arg doc structure

        Args:
            args (list): A list of tuples including the arg name, type, description, and python example struct
        
        Returns:
            a formatted string of the argument to inject into prompts such as the Args section of this docstring
        '''

        if not(args) or type(args[0]) == str: 
            return '\n'.join(a.strip() for a in args)
        
        formattted_arg_lst = []
        arg_template = "{name} ({arg_type}): {desc}"

        for name, arg_type, desc in args:
            if not isinstance(arg_type, str):
                arg_type = str(arg_type)
            formattted_arg_lst.appped(arg_template.format(
                name=name.strip(), arg_type=arg_type.strip(), desc=desc.strip()
            ))

        return "\n".join(formattted_arg_lst)
    
    def _format_examples(self, example):

        example_lst = []
        for i in example:
            if not isinstance(i, str):
                example_lst.append(str(i).strip())
            else:
                example_lst.append(i.strip())
        
        return example_lst

    def _create_api_documentation(self, spec: dict) -> str:
        '''
        Create the documentation string for each API from the spec given. This is then
        injected into the api and answer prompts to inform the AI how to use the API
        '''

        # Use this section to format the values
        formatted_spec = {}
        for k, v in spec.items():
            formatted_spec[k] = v

        template = '''
        Name:
        {name}

        Description:
        {description}

        Args:
        {args}

        Code Example:
        {code_example}

        Results Example:
        {example_results[0]}

        Results Description:
        {results_description}

        Example Query:
        {example_query[0]}

        Example Response:
        {example_response[0]}
        '''.format(
            **formatted_spec
        )

        return template