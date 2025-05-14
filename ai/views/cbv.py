import logging
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ai.models import VideoPrompt
from ai.gpt import generate_photo_descriptions, generate_images_from_descriptions
from ai.s3_utils import upload_image_to_s3, upload_video_to_s3
from ai.serializers import VideoPromptSerializer
from ai.nvidia import generate_video_from_images_with_nvidia
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
import base64
from moviepy import VideoFileClip, concatenate_videoclips
import uuid
import os
import time
from django.conf import settings
from ai.s3_utils import upload_image_to_s3, upload_video_to_s3, ensure_dir_exists, create_placeholder_video
import requests

logger = logging.getLogger('api_logger')


class GenerateVideo(APIView):
    @swagger_auto_schema(
        operation_summary="Generate video from user prompt",
        operation_description="This endpoint generates a video based on the given user prompt.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'prompt': openapi.Schema(type=openapi.TYPE_STRING, description="User's prompt to generate the video")
            },
            required=['prompt']
        ),
        responses={
            201: VideoPromptSerializer,
            400: "Bad Request: Prompt is missing or invalid",
            500: "Internal Server Error"
        }
    )

    def post(self, request):
        logger.info("POST request to GenerateVideo endpoint.")
        logger.info(f"MEDIA_ROOT is: {settings.MEDIA_ROOT}")
        logger.info(f"MEDIA_URL is: {settings.MEDIA_URL}")
        
        try:
            user_prompt = request.data.get("prompt")
            if not user_prompt:
                logger.warning("No prompt provided in request.")
                return Response({'error': 'No prompt provided'}, status=400)

            logger.info(f"Generating video for prompt: {user_prompt}")

            # Enable mock mode for this request
            os.environ['USE_MOCK_DATA'] = 'True'  

            descriptions = generate_photo_descriptions(user_prompt)
            if not descriptions:
                logger.error("Failed to generate descriptions.")
                return Response({'error': 'Failed to generate descriptions'}, status=500)

            image_urls = generate_images_from_descriptions(descriptions)
            if not image_urls:
                logger.error("Failed to generate images.")
                return Response({'error': 'Failed to generate images'}, status=500)

            # Store images locally
            s3_urls = []
            for url in image_urls:
                local_url = upload_image_to_s3(url)
                if local_url:
                    s3_urls.append(local_url)
                    # Verify file exists
                    file_path = os.path.join(settings.MEDIA_ROOT, local_url.replace('/media/', ''))
                    logger.info(f"Image saved to {file_path}, exists: {os.path.exists(file_path)}")
            
            # Ensure we have 5 images
            while len(s3_urls) < 5:
                timestamp = int(time.time()) + len(s3_urls)
                placeholder_url = f"https://picsum.photos/seed/{timestamp}/400/300"
                local_url = upload_image_to_s3(placeholder_url)
                if local_url:
                    s3_urls.append(local_url)
                    file_path = os.path.join(settings.MEDIA_ROOT, local_url.replace('/media/', ''))
                    logger.info(f"Placeholder image saved to {file_path}, exists: {os.path.exists(file_path)}")
                else:
                    s3_urls.append(f"https://picsum.photos/seed/{timestamp}/400/300")
            
            if len(s3_urls) > 5:
                s3_urls = s3_urls[:5]
                
            logger.info(f"Stored images locally: {s3_urls}")

            # Generate videos from the images
            video_urls = generate_video_from_images_with_nvidia(s3_urls)
            logger.info(f"Generated video URLs: {video_urls}")
            
            # Make sure we have valid video URLs
            s3_video_urls = []
            for url in video_urls:
                if url.startswith('data:'):
                    # It's base64 data - upload it
                    local_url = upload_video_to_s3(url)
                    if local_url:
                        s3_video_urls.append(local_url)
                        file_path = os.path.join(settings.MEDIA_ROOT, local_url.replace('/media/', ''))
                        logger.info(f"Video saved to {file_path}, exists: {os.path.exists(file_path)}")
                elif url.startswith('/media/'):
                    # It's already a local media URL
                    s3_video_urls.append(url)
                    file_path = os.path.join(settings.MEDIA_ROOT, url.replace('/media/', ''))
                    logger.info(f"Video already at {file_path}, exists: {os.path.exists(file_path)}")
                elif url.startswith('http'):
                    # It's a remote URL - download it
                    local_url = upload_video_to_s3(requests.get(url).content)
                    if local_url:
                        s3_video_urls.append(local_url)
                        file_path = os.path.join(settings.MEDIA_ROOT, local_url.replace('/media/', ''))
                        logger.info(f"Remote video saved to {file_path}, exists: {os.path.exists(file_path)}")
                    else:
                        s3_video_urls.append(url)  # Keep the remote URL

            # Ensure we have videos
            if not s3_video_urls:
                for i in range(5):
                    timestamp = int(time.time()) + i
                    folder_path = os.path.join(settings.MEDIA_ROOT, 'videos')
                    ensure_dir_exists(folder_path)
                    file_path = os.path.join(folder_path, f"placeholder_{timestamp}.mp4")
                    
                    if create_placeholder_video(file_path):
                        url = f"/media/videos/placeholder_{timestamp}.mp4"
                        s3_video_urls.append(url)
                        logger.info(f"Created fallback video at {file_path}, URL: {url}")

            # Make sure we have at least one video
            if not s3_video_urls:
                s3_video_urls.append("https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4")
                logger.info("Using external fallback video URL as last resort")
            
            # Use the first video URL as the final video
            final_video_url = s3_video_urls[0] if s3_video_urls else "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4"

            # Save everything to the database
            video_prompt = VideoPrompt.objects.create(
                prompt=user_prompt,
                arrTitles=descriptions,
                arrImages=s3_urls,
                arrVideos=s3_video_urls,
                finalVideo=final_video_url
            )

            serialized_data = VideoPromptSerializer(video_prompt).data
            logger.info("VideoPrompt successfully created and saved to database.")
            return Response(serialized_data, status=201)

        except Exception as e:
            logger.error(f"Error during video generation: {str(e)}")
            return Response({'error': str(e)}, status=500)

    @swagger_auto_schema(
        operation_summary="Retrieve all generated videos",
        operation_description="Returns a list of all video prompts with their associated data.",
        responses={
            200: VideoPromptSerializer(many=True),
        }
    )

    def get(self, request):
        logger.info("GET request to GenerateVideo endpoint.")
        generatedVideos = VideoPrompt.objects.all()
        serializer = VideoPromptSerializer(generatedVideos, many=True)
        return render(request, 'ai/video_list.html', {'videos': serializer.data})


class VideoDetail(APIView):
    @swagger_auto_schema(
        operation_summary="Retrieve a single video by ID",
        responses={
            200: VideoPromptSerializer,
            404: "Not Found"
        }
    )
    def get(self, request, pk):
        logger.info(f"GET request to VideoDetail for ID {pk}.")
        try:
            video = VideoPrompt.objects.get(id=pk)
            serializer = VideoPromptSerializer(video)
            return Response(serializer.data)
        except VideoPrompt.DoesNotExist:
            logger.warning(f"Video with ID {pk} not found.")
            return Response({'error': 'Video not found'}, status=404)

    @swagger_auto_schema(
        operation_summary="Update a video by ID",
        request_body=VideoPromptSerializer,
        responses={
            200: VideoPromptSerializer,
            400: "Bad Request",
            404: "Not Found"
        }
    )
    def put(self, request, pk):
        logger.info(f"PUT request to update VideoPrompt with ID {pk}.")
        try:
            video = VideoPrompt.objects.get(id=pk)
            serializer = VideoPromptSerializer(video, data=request.data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"VideoPrompt with ID {pk} updated successfully.")
                return Response(serializer.data)
            logger.warning(f"Validation failed for VideoPrompt update: {serializer.errors}")
            return Response(serializer.errors, status=400)
        except VideoPrompt.DoesNotExist:
            logger.warning(f"Video with ID {pk} not found.")
            return Response({'error': 'Video not found'}, status=404)

    @swagger_auto_schema(
        operation_summary="Delete a video by ID",
        responses={
            204: "No Content",
            404: "Not Found"
        }
    )
    def delete(self, request, pk=None):
        logger.info(f"DELETE request to remove VideoPrompt with ID {pk}.")
        try:
            video = VideoPrompt.objects.get(id=pk)
            video.delete()
            logger.info(f"VideoPrompt with ID {pk} deleted successfully.")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except VideoPrompt.DoesNotExist:
            logger.warning(f"Video with ID {pk} not found.")
            return Response({'error': 'Video not found'}, status=404)
