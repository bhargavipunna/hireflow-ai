import random

HEADERS = [
    {
        "User-Agent":
        "Mozilla/5.0"
    }
]


def get_random_headers():

    return random.choice(HEADERS)