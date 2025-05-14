# PixelTales

PixelTales is a modern social media platform built with Django that integrates video generation and AI-powered content creation capabilities.

## Features

- **Social Networking**: Connect with friends, share posts, and manage your profile
- **Realtime Chat**: Communicate with other users through WebSocket-powered chat rooms
- **AI-Powered Content Generation**: Create unique content using integrated AI models
- **Analytics Dashboard**: Track user engagement and platform metrics
- **Video Prompt Creation**: Generate videos based on text prompts

## Technology Stack

- **Backend**: Django, Django Channels, Celery
- **Frontend**: HTML, CSS, JavaScript
- **Database**: PostgreSQL (suggested)
- **Real-time Communication**: WebSockets via Django Channels
- **AI Integration**: OpenAI API for content generation
- **Video Generation**: Nvidia API integration

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/pixeltales.git
cd pixeltales
```

2. Create and activate a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root with the following variables:
```
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_URL=your_database_url
OPENAI_API_KEY=your_openai_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_STORAGE_BUCKET_NAME=your_s3_bucket_name
```

5. Run migrations:
```
python manage.py migrate
```

6. Start the development server:
```
python manage.py runserver
```

## Project Structure

- `social_network`: Core social media functionality
- `chat`: Real-time messaging system
- `ai`: AI-powered content generation
- `analytics`: User engagement tracking and visualization
- `pixeltales`: Main project configuration

## License

[MIT License](LICENSE)

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature-branch`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add some feature'`)
5. Push to the branch (`git push origin feature-branch`)
6. Open a Pull Request