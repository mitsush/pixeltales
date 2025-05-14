# In cartoonix/ai/gpt.py

import os
import random
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "False").lower() in ('true', '1', 't')
client = OpenAI(api_key=OPENAI_API_KEY)

# Add mock data for demo mode
MOCK_DESCRIPTIONS = [
    [
        "1. A mischievous cat with bright green eyes sits atop a globe, playfully batting at countries with its paw.",
        "2. The cat grows to gigantic size, now towering over skyscrapers, knocking buildings over like toys.",
        "3. Chaos ensues as the giant cat chases vehicles down highways, causing traffic jams and mayhem with a playful expression.",
        "4. The cat now sits in space, using Earth as a ball of yarn, unraveling continents with its claws.",
        "5. A final scene shows the cat napping peacefully among the remnants of civilization, purring contentedly."
    ],
    [
        "1. A colorful fantasy landscape with floating islands and crystal waterfalls under a purple sky.",
        "2. A wise old wizard teaching magic to young apprentices in an ancient library filled with glowing books.",
        "3. A dragon and a knight sharing tea instead of fighting, sitting at a small table on a hilltop.",
        "4. A futuristic city with flying vehicles and buildings that touch the clouds, glowing with neon lights.",
        "5. A group of diverse adventurers standing at the entrance to a mysterious cave, preparing for their journey."
    ]
]

MOCK_IMAGE_URLS = [
    "https://picsum.photos/seed/1/400/300",
    "https://picsum.photos/seed/2/400/300",
    "https://picsum.photos/seed/3/400/300",
    "https://picsum.photos/seed/4/400/300",
    "https://picsum.photos/seed/5/400/300"
]

system_prompt = """
# Original system prompt content
"""

def generate_photo_descriptions(user_prompt):
    """
    Generate five photo descriptions for a video storyline based on the user's request.

    :param user_prompt: User's text request
    :return: Array of five photo descriptions
    """
    # Use mock data if enabled or if there's an API error
    if USE_MOCK_DATA:
        print(f"Using mock descriptions for prompt: {user_prompt}")
        return random.choice(MOCK_DESCRIPTIONS)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create a video prompt for the following: {user_prompt}"}
            ]
        )
        
        photo_descriptions_text = response.choices[0].message.content
        
        lines = photo_descriptions_text.split('\n')
        
        photo_descriptions = []
        for line in lines:
            stripped_line = line.strip()
            if stripped_line and stripped_line[0].isdigit() and stripped_line[1] == '.':
                photo_descriptions.append(stripped_line)
        
        if len(photo_descriptions) != 5:
            raise ValueError("Unexpected number of descriptions received")
        
        print(f"Generated photo descriptions: {photo_descriptions}")
        return photo_descriptions
    except Exception as e:
        print(f"Error generating photo descriptions: {e}")
        # Fall back to mock data when API errors occur
        return random.choice(MOCK_DESCRIPTIONS)


def generate_images_from_descriptions(descriptions):
    """
    Generate images using DALL·E based on a list of descriptions.

    :param descriptions: List of text descriptions
    :return: List of URLs of generated images
    """
    # Use mock data if enabled or if there's an API error
    if USE_MOCK_DATA:
        print(f"Using mock image URLs")
        return MOCK_IMAGE_URLS
    
    image_urls = []
    try:
        for description in descriptions:
            response = client.images.generate(
                model="dall-e-3",
                prompt=description,
                size="1024x1024",
                quality="standard",
                n=1
            )
            image_url = response.data[0].url
            image_urls.append(image_url)
            print(f"Generated image URL: {image_url}")
        return image_urls
    except Exception as e:
        print(f"Error generating images: {e}")
        # Fall back to mock data when API errors occur
        return MOCK_IMAGE_URLS