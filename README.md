# ai_api

ai_api is a simple framework for building your own ChatGPT plugins using your own APIs. Inspired by the python Flask framework, ai_api provides a simple way to register API functions with ChatGPT, using your existng documentation to train the AI on how to call your data. 

## Example
```python
from ai_api import AiApi

app = AiApi()

@app.register_api()
def is_website_up(website: str):
    '''
    Tests if a website up and running

    Args:
        website (str): The full url of the website.
    
    Returns:
        Boolean: true of false if the website is up (true) or down (false)
    
    Code Example:
        website = "https://google.com"
        status = is_website_up(website)
    '''

    try:
        resp = requests.get(website, timeout=5)
        resp.raise_for_status()
        return True
    except:
        return False

app.execute_query("Is stackoverflow down right now?")
# AI >> It is working for me.

```

As we have seen, good documentation is actually a great source of prompt engineering for an AI to understand how to interact with your custom APIs. We build on this by generating prompts based on your own docs and then help an AI know when to call them.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Testing](#testing)
- [Contributing](#contributing)
- [Helpful Links](#helpful-links)

## Installation

ai_api can be installed via pip:

```bash
pip install ai_api
```

## Usage

1. Import AiApi

```python
from ai_api import AiApi
```

2. Configure and instantiate the AiApi object:
```python
app = AiApi(openai_api_key=open_ai_key, LOG_LEVEL="DEBUG")
```

3. Register your APIs using the register_api decorator:
```python
@app.register_api()
def my_api_function(arg1, arg2):
    # Do something with arg1 and arg2
    return result
```

4. As the LLM a question:
```python
response = app.execute_query("What is the answer to my question?")
```

## Testing

ai_api comes with a suite of tests that can be run using pytest. To run the tests, first install pytest:

```bash
pip install pytest
```

Then run the tests:

```bash
pytest
```

## Contributing

If you find a bug or have a feature request, please open an issue on GitHub. If you would like to contribute to the project, please fork the repository, make your changes, and submit a pull request.

## Helpful Links

- [Documentation](https://hedgineer.io/ai_api/)
- [GitHub Repository](https://github.com/hedgineer/ai_api)