from example_module import app
from random import randint

@app.register_api()
def get_random_number(low, high):
    '''
    Returns a random number between low and high

    Args:
        low (int): The lowest possible number
        high (int): The highest possible number

    Returns:
        int: A random number between low and high

        example:
        42

    Code Example:

        low = 0
        high = 100

        random_number = get_random_number(low, high)
    '''
    
    return randint(low, high)