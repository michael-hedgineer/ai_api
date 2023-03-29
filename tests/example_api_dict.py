import datetime

example1 = {
    "name": "risk_decomposition",
    "description": "Runs risk decomposition for an equities portfolio in order to tell a user what their volitility exposures are to different factors.",
    "code_example": \
        """
        portfolio = [("AAPL", 100), ("GOOG", 70), ("IBM", 200)]
        today = datetime.date.today()

        portfolio_risk = risk_decomposition(portfolio=portfolio, date=today)

        print(portfolio_risk)
        >> {
            "Beta_Dollar_Vol": 950000,
            "Tech_Dollar_Vol": 400000,
            "Momentum_Dollar_Vol": 350000
        }
        """.replace("        ", ""),
    "args": [
        'portfolio (list): A list of tuples containing the ticker and the quantity',
        'date (datetime.date): The date to run the risk decomposition for'
    ],
    "results_description": """
    A dict mapping each factor to the dollar volatility in the portfolio.
    Units are in dollars. The higher the value the higher the risk exposure.""".replace(
    "        ", ""),
    "example_results": [
        """
        {
            "Beta_Dollar_Vol": 950000,
            "Tech_Dollar_Vol": 400000,
            "Momentum_Dollar_Vol": 350000
        }
        """.replace('        ', '')
    ],
    "example_query": [
        "What are my factor volitility exposures in a portfolio with AAPL, GOOG, and IBM with 100, 70, and 200 shares of each?"
    ],
    "example_response": [
        "The largest factor exposure is Beta with a dollar volitility of $0.9 M. The second largest is Tech exposure with a dollar volitility of $400,000, and Momentum with $350,000."
    ],
    "example_kwargs": [{
        'portfolio': [['AAPL', 100], ['GOOG', 70], ['IBM', 200]],
        'date': 'datetime.date.today()'
    }]
}