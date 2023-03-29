# import requests
# from ai_api import AiApi

# open_ai_key = os.environ.get('OPENAI_API_KEY')

# app = AiApi(open_ai_key=open_ai_key)

# import yfinance as yf
# import pandas as pd

# def calculate_5_day_rolling_EPS_average(ticker):
#     stock = yf.Ticker(ticker)
#     stock_info = stock.info
    
#     if 'earningsData' not in stock_info or 'quarterly' not in stock_info['earningsData']:
#         print(f"No earnings data found for {ticker}")
#         return None
    
#     earnings_data = stock_info['earningsData']['quarterly']
#     eps_data = [{'Date': quarter['endDate'], 'EPS': quarter['earnings']} for quarter in earnings_data]
    
#     eps_df = pd.DataFrame(eps_data)
#     eps_df['Date'] = pd.to_datetime(eps_df['Date'])
#     eps_df.set_index('Date', inplace=True)
#     eps_df.sort_index(ascending=True, inplace=True)
    
#     eps_df['5_day_rolling_EPS_average'] = eps_df['EPS'].rolling(window=5).mean()
    
#     return eps_df

# # Example usage:
# ticker = 'AAPL'
# result = calculate_5_day_rolling_EPS_average(ticker)
# print(result)

from sec_api import QueryApi
import requests
import json
import os


def fetch_sec_filings(ticker, form_type):
    '''
     Fetches the most recent SEF filing for a given ticker and form type and retuns the filing text
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
    filing_text = []
    for filing in filings['filings']:
        r = requests.get(filing['linkToTxt'], headers=headers)
        filing_text.append(r.text)
    
    return filing_text

# Example usage:
ticker = 'AAPL'
form_type = '4'

result = fetch_sec_filings(ticker, form_type)
print(len(result[0]))