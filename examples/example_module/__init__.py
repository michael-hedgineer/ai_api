import pathlib, os, sys
sys.path.append(os.path.join(pathlib.Path(__file__).parent.parent.parent.resolve(), "src"))
from ai_api import AiApi

# Configure the API App
open_ai_key = os.environ.get('OPENAI_API_KEY')
app = AiApi(openai_api_key=open_ai_key, LOG_LEVEL="DEBUG")

#similar to flask import the modules
from example_module import module
