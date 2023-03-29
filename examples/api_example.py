
import requests

from sec_api import QueryApi


# Import local version of ai_api for examples
import pathlib, os, sys
sys.path.append(os.path.join(pathlib.Path(__file__).parent.parent.resolve(), "src"))
from ai_api import AiApi

# Configure the API App
open_ai_key = os.environ.get('OPENAI_API_KEY')
app = AiApi(openai_api_key=open_ai_key, LOG_LEVEL="DEBUG")

@app.register_api()
def fetch_sec_filings(ticker: str, form_type: str) -> str:
    '''
     Fetches the most recent SEF filing for a company and form type.

    Args:
        ticker (str): The stock symbol (eg. AAPL, IBM, GM)
        form_type (str): Filing type (eg. 4, 10-K, 10-Q)

    Returns:
        String: The exact filing text submitted to the SEC

        example:
        "SEC-Document-Text: 0001193125-20-001385.txt This transaction wqs made pursuant to the provisions"
    
    Code Example:

        ticker = "AAPL"
        form_type = "4"

        form_text = fetch_sec_filings(ticker, form_type)    
    '''

    api_key = os.getenv("SEC_API_KEY")  # Replace with your own API key
    query_api = QueryApi(api_key=api_key)

    query = {
        "query": {
            "query_string": {
                "query": f"ticker:{ticker} AND formType:{form_type}"
            }
        },
        "from": "0",
        "size": "1",
        "sort": [{"filedAt": {"order": "desc"}}]
    }

    headers = {
        'User-Agent': 'Hedgineer Services LLC info@hedgineer.io'
    }
    filings = query_api.get_filings(query)
    if filing := filings['filings']:
        r = requests.get(filing[0]['linkToTxt'], headers=headers)
        return r.text
    else:
        return None

print(app.execute_query("What was the most recent insider transaction for GM"))