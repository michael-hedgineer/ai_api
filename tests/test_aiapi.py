import json
import pytest
import datetime

from unittest.mock import MagicMock
from ai_api import AiApi
from example_api_dict import example1


class TestAiApi:

    @pytest.fixture(scope='class')
    def ai_api(self):
        api = AiApi()

        @api.register_api('risk_decomposition', api_dict=example1)
        def test_function(portfolio: list, date: datetime.date):
            return 'test'

        return api

    def test_identify_apis(self, ai_api, monkeypatch):
        expected_api_calls = {
            "apis": [
                {
                    'name': 'risk_decomposition',
                    'kwargs': example1['example_kwargs'][0]
                }
            ]
        }

        query = 'Sample query for identifying APIs'

        mock_openai = MagicMock()
        monkeypatch.setattr('ai_api.openai', mock_openai)
        mock_openai.ChatCompletion.create.return_value.choices = [{'message': {'content': json.dumps(expected_api_calls)}}]

        api_calls = ai_api.identify_apis(query)
        assert api_calls == expected_api_calls

    def test_execute_query(self, ai_api, monkeypatch):
        query = 'Sample query for executing APIs'
        expected_answer = 'Expected answer for the sample query'

        mock_identify_apis = MagicMock()
        monkeypatch.setattr(ai_api, 'identify_apis', mock_identify_apis)
        mock_identify_apis.return_value = {
            "apis": [
                {
                    'name': 'risk_decomposition',
                    'kwargs': example1['example_kwargs'][0]
                }
            ]
        }

        mock_openai = MagicMock()
        monkeypatch.setattr('ai_api.openai', mock_openai)
        mock_openai.ChatCompletion.create.return_value.choices = [{'message': {'content': expected_answer}}]

        answer = ai_api.execute_query(query)
        assert answer == expected_answer

    def test_ai_prompt_keys(self, ai_api, monkeypatch):
        
        ai_api._set_apis_prompt()
        for prompt in ai_api._api_prompts:
            assert prompt['role'] in ('user', 'assistant', 'system'), f"Invalid key {prompt['role']} in ai prompt keys"

    def test_ai_function_keys(self, ai_api, monkeypatch):

        assert 'risk_decomposition' in ai_api._apis.keys()

    def test_ai_prompt_len(self, ai_api, monkeypatch):

        assert len(ai_api._apis) == 1
    
    def test_ai_prompt_keys_len(self, ai_api, monkeypatch):
        
        ai_api._set_apis_prompt()
        assert len(ai_api._api_prompts) == 3
    
    def test_answer_prompt_keys(self, ai_api, monkeypatch):

        ai_api._set_apis_prompt()
        api_response = ai_api._generate_answer_prompts(['risk_decomposition'])
        for prompt in api_response:
            assert prompt['role'] in ('user', 'assistant', 'system'), f"Invalid key {prompt['role']} in ai prompt keys"
        
    def test_answer_prompt_len(self, ai_api, monkeypatch):

        ai_api._set_apis_prompt()
        api_response = ai_api._generate_answer_prompts(['risk_decomposition'])
        assert len(api_response) == 3

    def test_answer_prompt_keys_len(self, ai_api, monkeypatch):

        ai_api._set_apis_prompt()
        api_response = ai_api._generate_answer_prompts(['risk_decomposition'])
        assert len(api_response[0]) == 2

    def test_register_api_mismatched_names(self, ai_api, monkeypatch):

        with pytest.raises(AssertionError):
            @ai_api.register_api('mismatched_name', api_dict=example1)
            def mismatched_function():
                return 'test'
            
    def test_generate_answer_prompts_nonexistent_api(self, ai_api, monkeypatch):

        with pytest.raises(KeyError):
            ai_api._generate_answer_prompts(['nonexistent_api'])
            