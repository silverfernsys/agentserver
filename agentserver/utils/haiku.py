import random

# http://preshing.com/20121224/how-to-generate-a-sequence-of-unique-random-integers/


def permute(x):
    """
    permute returns a number in the range 0 to 9999
    that is unique for each x
    """
    prime = 9887  # https://primes.utm.edu/lists/small/10000.txt
    offset = 453
    maximum = 9999
    x = (x + offset) % maximum
    if (x >= prime):
        return x
    else:
        residue = (x * x) % prime
        if x <= (prime / 2):
            return residue
        else:
            return prime - residue


def haiku():
    return (random.choice(adjs), random.choice(nouns))


def haiku_name(id, separator='-'):
    (adj, noun) = haiku()
    return separator.join((adj, noun, str(permute(id))))


adjs = [
    "autumn", "hidden", "bitter", "misty", "silent", "empty", "dry", "dark",
    "summer", "icy", "delicate", "quiet", "white", "cool", "spring", "winter",
    "patient", "twilight", "dawn", "crimson", "wispy", "weathered", "blue",
    "billowing", "broken", "cold", "damp", "falling", "frosty", "green",
    "long", "late", "lingering", "bold", "little", "morning", "muddy", "old",
    "red", "rough", "still", "small", "sparkling", "throbbing", "shy",
    "wandering", "withered", "wild", "black", "young", "holy", "solitary",
    "fragrant", "aged", "snowy", "proud", "floral", "restless", "divine",
    "polished", "ancient", "purple", "lively", "nameless"
]


nouns = [
    "waterfall", "river", "breeze", "moon", "rain", "wind", "sea", "morning",
    "snow", "lake", "sunset", "pine", "shadow", "leaf", "dawn", "glitter",
    "forest", "hill", "cloud", "meadow", "sun", "glade", "bird", "brook",
    "butterfly", "bush", "dew", "dust", "field", "fire", "flower", "firefly",
    "feather", "grass", "haze", "mountain", "night", "pond", "darkness",
    "snowflake", "silence", "sound", "sky", "shape", "surf", "thunder",
    "violet", "water", "wildflower", "wave", "water", "resonance", "sun",
    "wood", "dream", "cherry", "tree", "fog", "frost", "voice", "paper",
    "frog", "smoke", "star"
]
