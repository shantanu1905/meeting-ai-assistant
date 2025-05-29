from app.helpers.constants import EMBEDDING_URL , RETRIVER_URL , OLLAMA_URL
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq , pipeline
import json
import requests
import torchaudio
import torch
import os
from app.helpers.modelloader import ModelRegistry
import math
from dotenv import load_dotenv

load_dotenv()

import redis



MAX_DURATION = 30  # seconds

def transcribe_audio(file_path: str) -> str:
    model = ModelRegistry.whisper_model
    processor = ModelRegistry.whisper_processor

    speech_array, sampling_rate = torchaudio.load(file_path)

    # Resample to 16kHz
    if sampling_rate != 16000:
        resampler = torchaudio.transforms.Resample(orig_freq=sampling_rate, new_freq=16000)
        speech_array = resampler(speech_array)

    # Convert stereo to mono
    if speech_array.shape[0] > 1:
        speech_array = torch.mean(speech_array, dim=0, keepdim=True)

    waveform = speech_array.squeeze(0)
    chunk_size = MAX_DURATION * 16000  # samples per chunk
    total_samples = waveform.shape[0]
    num_chunks = math.ceil(total_samples / chunk_size)

    transcription = ""

    for i in range(num_chunks):
        start = i * chunk_size
        end = min(start + chunk_size, total_samples)
        chunk = waveform[start:end]

        input_features = processor(
            chunk.numpy(),
            sampling_rate=16000,
            return_tensors="pt"
        ).input_features

        with torch.no_grad():
            predicted_ids = model.generate(input_features)

        text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        transcription += text + "\n"

    return transcription.strip()

def chunk_text(text, max_chars=1000):
    paragraphs = text.split("\n")
    chunks = []
    chunk = ""

    for para in paragraphs:
        if len(chunk) + len(para) < max_chars:
            chunk += para + "\n"
        else:
            chunks.append(chunk.strip())
            chunk = para + "\n"
    if chunk:
        chunks.append(chunk.strip())
    return chunks

def summarize_text(text: str) -> str:

    summarizer = ModelRegistry.summarizer
    if summarizer is None:
        raise ValueError("Summarizer model not loaded")

    chunks = chunk_text(text)
    summary_parts = []

    for chunk in chunks:
        if not chunk.strip():
            continue

        input_len = len(chunk.split())
        max_len = min(130, int(input_len * 0.8))
        min_len = max(30, int(max_len * 0.5))

        try:
            result = summarizer(
                chunk,
                max_length=max_len,
                min_length=min_len,
                do_sample=False
            )
            summary_parts.append(result[0]["summary_text"])
        except Exception as e:
            summary_parts.append(f"[Summary error]: {str(e)}")

    return "\n".join(summary_parts).strip()

# def summarize_text(text: str, max_chunk_length: int = 1024) -> str:
#     if not text.strip():
#         return "Transcript is empty."

#     chunks = []
#     current_chunk = ""
#     for paragraph in text.split("\n"):
#         if len(current_chunk) + len(paragraph) < max_chunk_length:
#             current_chunk += paragraph + "\n"
#         else:
#             chunks.append(current_chunk.strip())
#             current_chunk = paragraph + "\n"
#     if current_chunk:
#         chunks.append(current_chunk.strip())

#     summaries = []
#     for chunk in chunks:
#         try:
#             summary = summarizer(chunk, max_length=130, min_length=30, do_sample=False)[0]['summary_text']
#             summaries.append(summary)
#         except Exception as e:
#             summaries.append("[Error summarizing chunk]")

#     return "\n".join(summaries)



def get_embedding(text, url = EMBEDDING_URL):
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": [text]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise error for bad responses (4xx or 5xx)

        embedding = response.json()
        return embedding  # Usually a list of vectors, e.g., [[0.123, 0.456, ...]]
    except requests.exceptions.RequestException as e:
        print(f"Error communicating with embedding service: {e}")
        return None



def retrieve_similar_documents(text, embedding, index_name, k=4, search_type="similarity", url=RETRIVER_URL):
    if url is None:
        raise ValueError("Retrieval URL must be provided")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "text": text,
        "embedding": embedding,  # API expects a 2D list
        "search_type": search_type,
        "k": k,
        "index_name": index_name
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        data = response.json()

        # Extract only the text fields from retrieved_docs
        return data.get("retrieved_docs", [])

    except requests.exceptions.RequestException as e:
        print(f"Error in retrieval request: {e}")
        return []


def build_qa_prompt(question, context_chunks):
    context_text = "\n\n---\n\n".join(chunk["text"] for chunk in context_chunks)
    prompt = (
        "You are a helpful assistant. Use the following extracted passages from meeting transcripts "
        "to answer the user’s question as accurately as possible.\n\n"
        f"Context:\n{context_text}\n\n"
        f"Question: {question}\n\n"
        "Answer (in one concise sentence):"
    )
    return prompt



def meeting_minutes_prompt(context_chunks):
    CONTEXT = (
        "You are a team assistant and support the team with its daily work.\n"
    )

    INSTRUCTIONS_CREATE_MEETING_MINUTES = """
                    Your task is to create the meeting minutes for the transcript provided by the user.
                    Proceed step-by-step:
                    1. Read through the transcript carefully.
                    2. Start by writing a brief **Summary** of the overall meeting.
                    3. Extract all decisions that were discussed and add them under the title **Decisions**.
                    4. Identify all tasks and responsibilities discussed in the meeting. Add them to the **Action Items** section, including assignees and deadlines if mentioned.
                    5. Under the title **Additional Notes**, include any discussion points that were important but didn't fit in the previous categories.
                    6. Return only the final meeting minutes to the user.
                """

    context_text = "\n\n---\n\n".join(chunk["text"] for chunk in context_chunks)

    prompt = (
        f"{CONTEXT}\n"
        f"{INSTRUCTIONS_CREATE_MEETING_MINUTES}\n\n"
        "Transcript:\n"
        f"{context_text}\n\n"
        "Generate the meeting minutes below:\n"
        "**Meeting Minutes:**\n"
    )

    return prompt
import re
def parse_meeting_minutes(raw_text: str) -> dict:
    sections = {
        "summary": "",
        "decisions": "",
        "action_items": "",
        "additional_notes": ""
    }

    patterns = {
        "summary": r"\*\*Summary:\*\*\s*(.*?)(?=\n\n\*\*Decisions:|\Z)",
        "decisions": r"\*\*Decisions:\*\*\s*(.*?)(?=\n\n\*\*Action Items:|\Z)",
        "action_items": r"\*\*Action Items:\*\*\s*(.*?)(?=\n\n|\Z)",
        "additional_notes": r"\*\*Additional Notes:\*\*\s*(.*?)(?=\n\n|\Z)"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, raw_text, re.DOTALL | re.IGNORECASE)
        if match:
            sections[key] = match.group(1).strip()

    return sections



def generate_llm_answer(prompt, model="gemma2:2b", stream=False):
    url = OLLAMA_URL
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    
    data = resp.json()
    if "response" not in data:
        raise ValueError(f"Unexpected response format: {data}")
    
    return data["response"]



def answer_question(question, embedding, index_name):
    # a) Get context
    contexts = retrieve_similar_documents(question, embedding, index_name)
    # b) Build prompt
    prompt = build_qa_prompt(question, contexts)
    # c) Generate answer
    answer = generate_llm_answer(prompt)
    return answer




def analyze_sentiment(lines):
    """
    Analyzes the sentiment of each line in a list of strings, safely handling long inputs.

    Args:
        lines (List[str]): List of transcript lines or sentences.

    Returns:
        List[Dict]: A list of dictionaries with line, sentiment label, and confidence score.
    """
    if ModelRegistry.sentiment_analyzer is None:
        raise ValueError("Sentiment analyzer model not loaded.")

    tokenizer = ModelRegistry.sentiment_analyzer.tokenizer
    max_length = tokenizer.model_max_length

    results = []
    for line in lines:
        if not line.strip():
            continue  # Skip empty lines

        try:
            # Truncate line if too long
            tokens = tokenizer.encode(line, truncation=True, max_length=max_length)
            truncated_line = tokenizer.decode(tokens, skip_special_tokens=True)

            result = ModelRegistry.sentiment_analyzer(truncated_line)[0]
            results.append({
                "line": truncated_line,
                "label": result['label'],
                "score": round(result['score'], 3)
            })
        except Exception as e:
            results.append({
                "line": line,
                "label": "error",
                "score": 0.0,
                "error": str(e)
            })

    return results





class MeetingCleanup:
    def __init__(self, ):
        self.redis_client = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=os.getenv("REDIS_DB"))

    def delete_rag_redis_vectors(self, pattern_string: str) -> int:
        """
        Deletes all Redis keys matching the given pattern (e.g., vector embeddings).
        """
        pattern = f"doc:{pattern_string}:*"
        deleted_count = 0

        try:
            for key in self.redis_client.scan_iter(match=pattern, count=100):
                self.redis_client.delete(key)
                deleted_count += 1

            print(f"✅ Deleted {deleted_count} keys matching pattern '{pattern}'.")
            return deleted_count

        except Exception as e:
            print(f"❌ Error deleting keys: {e}")
            return 0

    def delete_all_meeting_files(self, library_entry) -> list:
        """
        Delete all file paths stored in the MeetingLibrary model entry.
        """
        deleted_files = []
        if library_entry:
            for column in library_entry.__table__.columns:
                if 'path' in column.name:
                    path = getattr(library_entry, column.name)
                    if path and os.path.exists(path):
                        try:
                            os.remove(path)
                            deleted_files.append(path)
                        except Exception as e:
                            print(f"Failed to delete file {path}: {str(e)}")
        return deleted_files
