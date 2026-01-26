"""Name generator for execution contexts."""

import random


# Adjectives that describe something positively
ADJECTIVES = [
    "awesome", "beautiful", "elegant", "graceful", "magnificent",
    "stunning", "brilliant", "charming", "delightful", "exquisite",
    "fantastic", "glorious", "impressive", "lovely", "majestic",
    "marvelous", "peaceful", "radiant", "serene", "splendid",
    "superb", "wonderful", "enchanting", "vibrant", "dazzling",
    "pristine", "sublime", "divine", "remarkable", "spectacular"
]

# Famous places around the world
PLACES = [
    "paris", "london", "tokyo", "rome", "sydney",
    "newyork", "barcelona", "venice", "amsterdam", "prague",
    "vienna", "dublin", "florence", "santorini", "kyoto",
    "singapore", "istanbul", "cairo", "athens", "bali",
    "maldives", "iceland", "switzerland", "norway", "zealand",
    "tahiti", "fiji", "monaco", "dubai", "bangkok",
    "hongkong", "seoul", "beijing", "mumbai", "rio"
]


def generate_name() -> str:
    """Generate a random name like 'awesome-paris'.
    
    Returns:
        Generated name in format: adjective-place
    """
    adjective = random.choice(ADJECTIVES)
    place = random.choice(PLACES)
    return f"{adjective}-{place}"
