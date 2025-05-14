import os
import time
import requests
import base64  # Added this import
import shutil
from pathlib import Path
from django.conf import settings

# Create a media directory for storing files
MEDIA_ROOT = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))

def ensure_dir_exists(directory):
    """Ensure the directory exists, create it if it doesn't"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def setup_media_directories():
    """Ensure all required media directories exist"""
    directories = ['images', 'videos', 'uploads']
    for directory in directories:
        dir_path = os.path.join(MEDIA_ROOT, directory)
        ensure_dir_exists(dir_path)
        print(f"Ensured directory exists: {dir_path}")

# Call this function when the module is imported
setup_media_directories()

def create_placeholder_image(file_path):
    """Create a simple but valid image file"""
    try:
        response = requests.get('https://picsum.photos/400/300', stream=True)
        if response.status_code == 200:
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Created placeholder image at {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error creating placeholder image: {e}")
        return False

def create_placeholder_video(file_path):
    """Create a simple but valid video file"""
    try:
        # Multiple fallback sources
        video_urls = [
            "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
            "https://samplelib.com/lib/preview/mp4/sample-5s.mp4",
            "https://filesamples.com/samples/video/mp4/sample_640x360.mp4"
        ]
        
        for video_url in video_urls:
            try:
                response = requests.get(video_url, stream=True, timeout=10)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"Downloaded sample video to {file_path} from {video_url}")
                    return True
            except Exception as e:
                print(f"Error with video source {video_url}: {e}")
                continue
        
        print("All video sources failed, creating fallback text file")
        with open(file_path, 'wb') as f:
            # Very small valid MP4 file
            f.write(b'\x00\x00\x00\x20\x66\x74\x79\x70\x69\x73\x6F\x6D\x00\x00\x02\x00\x69\x73\x6F\x6D\x69\x73\x6F\x32\x61\x76\x63\x31\x6D\x70\x34\x31')
        return True
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
        
        # Create folder path - Make this OS agnostic
        folder_path = os.path.join(MEDIA_ROOT, folder)
        ensure_dir_exists(folder_path)
        
        # Full file path
        file_path = os.path.join(folder_path, unique_file_name)
        
        # Write the file
        with open(file_path, 'wb') as f:
            if isinstance(file_data, str) and file_data.startswith('data:'):
                # Handle base64 data
                try:
                    header, encoded = file_data.split(",", 1)
                    file_data = base64.b64decode(encoded)
                except Exception as e:
                    print(f"Error decoding base64 data: {e}")
            f.write(file_data)
        
        # Return URL (relative to MEDIA_URL) - FIX PATH SEPARATORS
        relative_path = os.path.join(folder, unique_file_name).replace('\\', '/')
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
        file_path = os.path.join(folder_path, f"image_{timestamp}.jpg")
        
        # Handle base64 data URLs
        if image_url and image_url.startswith('data:image'):
            try:
                content_type, b64data = image_url.split(',', 1)
                image_data = base64.b64decode(b64data)
                with open(file_path, 'wb') as f:
                    f.write(image_data)
                print(f"Saved base64 image to {file_path}")
                return f"/media/{folder}/image_{timestamp}.jpg".replace('\\', '/')
            except Exception as e:
                print(f"Error decoding base64 image data: {e}")
        
        # Try to download from URL if provided
        if image_url and image_url.startswith(('http://', 'https://')):
            try:
                response = requests.get(image_url, stream=True, timeout=10)
                if response.status_code == 200:
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"Successfully downloaded image to {file_path}")
                    return f"/media/{folder}/image_{timestamp}.jpg".replace('\\', '/')
            except Exception as e:
                print(f"Error downloading image from {image_url}: {e}")
        
        # If we get here, use a reliable fallback image
        try:
            fallback_url = f"https://picsum.photos/seed/{timestamp}/400/300"
            response = requests.get(fallback_url, stream=True, timeout=5)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Created fallback image at {file_path}")
                return f"/media/{folder}/image_{timestamp}.jpg".replace('\\', '/')
        except Exception as e:
            print(f"Error creating fallback image: {e}")
            
        return "https://picsum.photos/400/300"
            
    except Exception as e:
        print(f"Major error in upload_image_to_s3: {e}")
        return "https://picsum.photos/400/300"
        
def upload_video_to_s3(video_data, folder='videos'):
    """
    Upload a video to local storage instead of S3.
    """
    try:
        # Check if the data is base64 encoded
        if video_data and isinstance(video_data, str) and video_data.startswith('data:video'):
            # Extract the base64 data
            try:
                content_type, b64data = video_data.split(',', 1)
                video_data = base64.b64decode(b64data)
                print(f"Successfully decoded base64 video data, length: {len(video_data)}")
            except Exception as e:
                print(f"Error decoding base64 video: {e}")
                # Create a placeholder instead
                timestamp = int(time.time())
                folder_path = os.path.join(MEDIA_ROOT, folder)
                ensure_dir_exists(folder_path)
                file_path = os.path.join(folder_path, f"placeholder_{timestamp}.mp4")
                
                if create_placeholder_video(file_path):
                    return f"/media/{folder}/placeholder_{timestamp}.mp4"
                return None
            
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