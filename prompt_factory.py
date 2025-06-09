import random

# --- Ingredients for the Prompt Factory ---

BASE_SHAPES = [
    "a square plate",
    "a rectangular plate",
    "a circular plate",
    "a ring-shaped plate",
    "an L-shaped bracket",
    "a T-shaped bracket",
    "a flat bar",
]

FEATURES = [
    "a large hole in the center",
    "a series of small mounting holes near the edge",
    "a rectangular cutout on one side",
    "a slotted hole for adjustment",
    "rounded corners",
    "notched corners",
    "a reinforcing rib across the center",
    "a triangular gusset for support",
    "a threaded hole for a sensor",
]

DIMENSIONS = [
    "with a major dimension of about 50mm",
    "with a major dimension of about 100mm",
    "with a major dimension of about 200mm",
    "that is roughly 10mm thick",
    "that is roughly 5mm thick",
]

MATERIAL = [
    "made of aluminum",
    "made of stainless steel",
    "made of ABS plastic",
    "made of titanium",
]


def generate_random_prompt():
    """
    Generates a random, descriptive prompt for a mechanical part.
    """
    # 1. Start with a base shape
    prompt = random.choice(BASE_SHAPES)

    # 2. Add a couple of features
    num_features = random.randint(1, 3)
    selected_features = random.sample(FEATURES, num_features)
    prompt += " with " + " and ".join(selected_features)

    # 3. Add a dimension
    prompt += ", " + random.choice(DIMENSIONS)

    # 4. Add a material (optional)
    if random.random() > 0.5:
        prompt += ", " + random.choice(MATERIAL)
    
    prompt += "."

    return prompt

if __name__ == '__main__':
    print("--- Generating 5 Random Drawing Prompts ---")
    for i in range(5):
        print(f"{i+1}: {generate_random_prompt()}") 