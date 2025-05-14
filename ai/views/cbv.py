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
            for i in range(5):  # Ensure we have 5 images
                timestamp = int(time.time()) + i
                # Use a different image for each position
                placeholder_url = f"https://picsum.photos/seed/{timestamp}/400/300"
                local_url = upload_image_to_s3(placeholder_url)
                if local_url:
                    s3_urls.append(local_url)
                else:
                    s3_urls.append(f"https://via.placeholder.com/400x300/87CEEB/000000?text=Image+{i+1}")

            
            if not s3_urls:
                logger.error("Failed to upload images to S3.")
                return Response({'error': 'Failed to upload images to S3'}, status=500)
                
            logger.info(f"Stored images locally: {s3_urls}")

            if len(s3_urls) < 5:
                for i in range(len(s3_urls), 5):
                    s3_urls.append(f"https://via.placeholder.com/400x300/87CEEB/000000?text=Image+{i+1}")
            elif len(s3_urls) > 5:
                s3_urls = s3_urls[:5]

            # For mock mode, create placeholder videos
            s3_video_urls = []
            for i in range(len(s3_urls)):
                # Create a placeholder video and get its URL
                timestamp = int(time.time()) + i
                folder_path = os.path.join(settings.MEDIA_ROOT, "videos")
                ensure_dir_exists(folder_path)
                file_path = os.path.join(folder_path, f"placeholder_{timestamp}.mp4")
                
                if create_placeholder_video(file_path):
                    s3_video_urls.append(f"/media/videos/placeholder_{timestamp}.mp4")

            if not s3_video_urls:
                logger.error("Failed to create placeholder videos.")
                return Response({'error': 'Failed to create videos'}, status=500)

            logger.info(f"Created placeholder videos: {s3_video_urls}")

            # Use the first video URL as the final video
            final_video_url = s3_video_urls[0] if s3_video_urls else ""

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
