import base64
import requests
import random
import time
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("NVIDIA_API_KEY")
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "False").lower() in ('true', '1', 't')

# Add mock data for demo mode
MOCK_VIDEOS = [
    "data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAABMptZGF0AAACpAYF//+0",
    "data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAABMptZGF0AAACpAYF//+1",
    "data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAABMptZGF0AAACpAYF//+2",
    "data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAABMptZGF0AAACpAYF//+3",
    "data:video/mp4;base64,AAAAIGZ0eXBpc29tAAACAGlzb21pc28yYXZjMW1wNDEAAAAIZnJlZQAABMptZGF0AAACpAYF//+4"
]

def generate_video_from_images_with_nvidia(image_urls):
    """ Generate video using Nvidia's API based on a list of image URLs.
    :param image_urls: List of URLs of the images used for video generation
    :return: List of real video URLs (not base64 data)
    """
    from django.conf import settings
    from ai.s3_utils import ensure_dir_exists, create_placeholder_video
    
    # Use mock data if enabled or if there's an API error
    if USE_MOCK_DATA:
        print(f"Using mock videos")
        
        # Create actual video files instead of base64 data
        video_paths = []
        for i in range(min(5, len(image_urls))):
            timestamp = int(time.time()) + i
            folder_path = os.path.join(settings.MEDIA_ROOT, 'videos')
            ensure_dir_exists(folder_path)
            
            file_path = os.path.join(folder_path, f"placeholder_{timestamp}.mp4")
            
            if create_placeholder_video(file_path):
                video_url = f"/media/videos/placeholder_{timestamp}.mp4"
                print(f"Created mock video at {file_path}, URL: {video_url}")
                video_paths.append(video_url)
            else:
                # Emergency fallback - use a public video URL
                video_paths.append("https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4")
        
        return video_paths
    
    # Original API call code for non-mock mode
    api_url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-video-diffusion"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {API_KEY}"
    }
    
    video_results = []
    
    for image_url in image_urls:
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = response.content
            image_base64 = f"data:image/png;base64,{base64.b64encode(image_data).decode()}"
            
            payload = {
                "image": image_base64,
                "seed": 0,
                "cfg_scale": 1.8,
                "motion_bucket_id": 127
            }
            
            response = requests.post(api_url, json=payload, headers=headers)
            response_data = response.json()
            
            if response_data.get('video'):
                video_results.append(response_data['video'])
                print(response_data['video'])
            else:
                print(f"Failed to generate video for image URL: {image_url}")
        
        except Exception as e:
            print(f"Error in calling Nvidia API for image {image_url}: {e}")
    
    # Fall back to mock data if we couldn't generate any videos
    if not video_results:
        return ["https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"]
        
    return video_results