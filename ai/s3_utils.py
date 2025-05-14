import os
import time
import requests
import shutil
from pathlib import Path
from django.conf import settings

# Create a media directory for storing files
MEDIA_ROOT = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))

def ensure_dir_exists(directory):
    """Ensure the directory exists, create it if it doesn't"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def create_placeholder_image(file_path):
    """Create a simple but valid image file"""
    # Download a real placeholder image from a public service
    try:
        response = requests.get('https://via.placeholder.com/400x300/333333/FFFFFF?text=PixelTales+Mock+Image')
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"Error creating placeholder image: {e}")
        return False

def create_placeholder_video(file_path):
    """Create a simple but valid video file"""
    try:
        # Download a small sample video from a public domain source
        video_url = "https://samplelib.com/lib/preview/mp4/sample-5s.mp4"  # 5-second sample video
        response = requests.get(video_url)
        
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded sample video to {file_path}")
            return True
        else:
            print(f"Failed to download sample video, status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error creating placeholder video: {e}")
        return False

def upload_to_s3(file_data, original_file_name, folder=''):
    """
    Save a file to local storage instead of S3.
    """
    try:
        # Create timestamp for unique filename
        timestamp = int(time.time())
        
        # Get file extension
        file_extension = os.path.splitext(original_file_name)[1]
        if not file_extension:
            file_extension = '.jpg' if folder == 'images' else '.mp4'
        
        # Create unique filename
        unique_file_name = f"{timestamp}{file_extension}"
        
        # Create folder path
        folder_path = os.path.join(MEDIA_ROOT, folder)
        ensure_dir_exists(folder_path)
        
        # Full file path
        file_path = os.path.join(folder_path, unique_file_name)
        
        # Write the file
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Return URL (relative to MEDIA_URL)
        relative_path = os.path.join(folder, unique_file_name)
        url = f"/media/{relative_path}"
        
        print(f"Saved file to {file_path}")
        return url
    except Exception as e:
        print(f"Error saving file locally: {e}")
        return None

def upload_image_to_s3(image_url, folder='images'):
    """
    Upload an image to local storage by URL.
    """
    try:
        # If this is already a local URL, just return it
        if image_url and image_url.startswith('/media/'):
            return image_url
            
        # Create timestamp and paths
        timestamp = int(time.time())
        folder_path = os.path.join(MEDIA_ROOT, folder)
        ensure_dir_exists(folder_path)
        file_path = os.path.join(folder_path, f"placeholder_{timestamp}.jpg")
        
        # Download from URL if provided
        if image_url and not image_url.startswith(('http://', 'https://')):
            image_url = f"https://picsum.photos/seed/{timestamp}/400/300"
            
        # Try to download the image
        if image_url and image_url.startswith(('http://', 'https://')):
            try:
                response = requests.get(image_url, stream=True, timeout=5)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"Successfully downloaded image to {file_path}")
                    return f"/media/{folder}/placeholder_{timestamp}.jpg"
            except Exception as e:
                print(f"Error downloading image from {image_url}: {e}")
        
        # If we get here, we need to create a fallback image
        try:
            # Try to download a placeholder
            fallback_url = f"https://via.placeholder.com/400x300/87CEEB/000000?text=Image+{timestamp}"
            response = requests.get(fallback_url, stream=True, timeout=5)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Created fallback image at {file_path}")
                return f"/media/{folder}/placeholder_{timestamp}.jpg"
        except Exception as e:
            print(f"Error creating fallback image: {e}")
        
        # Last resort: create a simple colored rectangle
        try:
            # Create a solid color image using PIL
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (400, 300), color=(135, 206, 235))  # Sky blue
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (399, 299)], outline=(0, 0, 0))
            img.save(file_path)
            print(f"Created PIL image at {file_path}")
            return f"/media/{folder}/placeholder_{timestamp}.jpg"
        except Exception as e:
            print(f"Error creating PIL image: {e}")
            
        # If all else fails, return a placeholder URL directly
        return "https://via.placeholder.com/400x300/FF0000/FFFFFF?text=Error"
            
    except Exception as e:
        print(f"Major error in upload_image_to_s3: {e}")
        return "https://via.placeholder.com/400x300/FF0000/FFFFFF?text=Error"
        
        
def upload_video_to_s3(video_data, folder='videos'):
    """
    Upload a video to local storage instead of S3.
    """
    try:
        file_name = f"video_{int(time.time())}.mp4"
        return upload_to_s3(video_data, file_name, folder=folder)
    except Exception as e:
        print(f"Error uploading video to local storage: {e}")
        
        # Create a valid placeholder video
        timestamp = int(time.time())
        folder_path = os.path.join(MEDIA_ROOT, folder)
        ensure_dir_exists(folder_path)
        file_path = os.path.join(folder_path, f"placeholder_{timestamp}.mp4")
        
        if create_placeholder_video(file_path):
            return f"/media/{folder}/placeholder_{timestamp}.mp4"
        return None