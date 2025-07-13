# AI Meeting Assistant

## Introduction

**AI Meeting Assistant** is an intelligent post-meeting automation platform built to transform how teams manage and revisit meetings. By leveraging advanced AI and a modular architecture powered by **OPEA microservices**, this tool eliminates the need for manual note-taking, enhances productivity, and makes meetings more accessible and actionable.

Users can effortlessly upload their meeting data—whether transcripts or audio/video recordings (e.g., `.mp3`, `.wav`, `.mp4`)—and let the assistant handle the rest. The system processes content automatically, providing valuable insights, summaries, and actionable outcomes without having to rewatch or re-read lengthy discussions.

---

## Key Features

- 🎙 **Automatic Transcription**  
  Converts audio/video recordings into accurate, searchable text.

- 📝 **Meeting Summarization**  
  Generates concise summaries for quick review and better understanding.

- 📋 **Actionable Minutes of Meeting (MoM)**  
  Automatically detects and organizes key points, decisions, and action items from the discussion.

- ❓ **Semantic Q&A**  
  Enables users to query the meeting content using natural language questions and receive context-aware answers.

- 😊 **Sentiment Analysis**  
  Performs line-by-line speaker sentiment analysis to gauge tone and engagement.


---

## Why Use AI Meeting Assistant?

- Save time by eliminating manual note-taking  
- Quickly identify key decisions and follow-ups  
- Enhance team collaboration and accountability  
- Revisit meeting content effortlessly using search and Q&A  
- Improve inclusivity with multilingual support and transcription accessibility


## Tech Stack

### 🧠 Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (via SQLAlchemy ORM)
- **Authentication**: JWT-based authentication with OTP verification
- **File Storage**: Local server file system
- **Vector Database**: Redis with RediSearch

### ⚙️ OPEA Microservices
- **ASR Microservice**: Converts audio/video files to text using automatic speech recognition.
- **Dataprep Microservice**: Cleans and processes transcript text and stores embeddings in the vector database.
- **Embeddings Microservice**: Generates vector embeddings from textual data.
- **Retriever Microservice**: Enables fast semantic search across meeting content.
- **LLM Microservice**: Powers natural language Q&A and generates contextual summaries.
- **Document Summary Microservice**: Extracts concise Minutes of Meeting (MoM) from transcripts.

### 💻 Frontend
- **Build Tool**: Vite
- **Framework**: React.js
- **UI Library**: Material UI
- **State Management**: Redux Toolkit
- **Repo Link**: [https://github.com/sam-79/SyncAgenda](https://github.com/sam-79/SyncAgenda)

### Architecture

![Architecture](https://github.com/shantanu1905/meeting-ai-assistant/blob/main/documentation/Architecture%20Diagram.drawio%20(1).png)



### 🐳 Containerization
- **Docker**: Used for microservice containerization and deployment


## 🚀 Project Setup

Follow these steps to set up and run the AI Meeting Assistant locally.

---

### 1. Clone the Repository

```bash
git https://github.com/shantanu1905/meeting-ai-assistant.git
cd ai-meeting-assistant

```

### 2. Environment Configuration
Create a .env file in both the backend directories (or wherever appropriate), and add necessary environment variables.

```
# Retrieve environment variables
POSTGRES_HOST=127.0.0.1
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_PORT=5432


HOST_URL = 127.0.0.1:8000

JWT_SECRET=e56623570e0a0152989fd38e13da9cd6eb7031e4e039e939ba845167ee59b496
RABBITMQ_URL=localhost


GMAIL_ADDRESS=your-mail
GMAIL_PASSWORD=your-mail-password
HUGGING_FACE_API_KEY=your-api-key

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0


```

## 3. Docker Setup
Make sure you have Docker and Docker Compose installed.
```
docker-compose up 
```

This will:

Start all OPEA microservices

Launch PostgreSQL and Redis.

## 4.  Backend Setup
```
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
API Docs available at: http://localhost:8000/docs


