import json
import requests
from app.helpers.constants import EMBEDDING_URL , RETRIVER_URL , OLLAMA_URL
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq
import torchaudio
import torch
import os


processor = AutoProcessor.from_pretrained("openai/whisper-tiny")
model = AutoModelForSpeechSeq2Seq.from_pretrained("openai/whisper-tiny")
model.eval()

def transcribe_audio(file_path: str) -> str:
    # Load audio
    speech_array, sampling_rate = torchaudio.load(file_path)

    # Resample to 16kHz
    if sampling_rate != 16000:
        resampler = torchaudio.transforms.Resample(orig_freq=sampling_rate, new_freq=16000)
        speech_array = resampler(speech_array)

    # Convert stereo to mono
    if speech_array.shape[0] > 1:
        speech_array = torch.mean(speech_array, dim=0, keepdim=True)

    # Preprocess and transcribe
    input_features = processor(
        speech_array.squeeze().numpy(),
        sampling_rate=16000,
        return_tensors="pt"
    ).input_features

    with torch.no_grad():
        predicted_ids = model.generate(input_features)

    transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
    return transcription





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

    EXAMPLE_OUTPUT = """
            **Summary:**

            The team met to finalize the marketing strategy for Q3 and align on the timeline for the Version 2.1 product launch.

            **Decisions:**

            **Action Items:**

            Alice (Marketing Lead): Prepare campaign assets by July 5th.
            John (Product Manager): Coordinate beta testing with QA team.
            Meera (Sales): Draft customer communication for new release.

            **Additional Notes:**

            - Budget reallocation for paid campaigns will be reviewed in next finance sync.
            - Potential partnership with Growthly discussed; requires follow-up.
            """

    context_text = "\n\n---\n\n".join(chunk["text"] for chunk in context_chunks)

    prompt = (
        f"{CONTEXT}\n"
        f"{INSTRUCTIONS_CREATE_MEETING_MINUTES}\n\n"
        "Transcript:\n"
        f"{context_text}\n\n"
        "Generate the meeting minutes below:\n"
        f"{EXAMPLE_OUTPUT}\n\n"
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
        "action_items": r"\*\*Action Items:\*\*\s*(.*?)(?=\n\n\*\*Additional Notes:|\Z)",
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


























# # Example usage
# # Assuming you have a vector from embedding service
# text = "tell me about problem solving"
# example_embedding = [0.1, 0.2, 0.3, ...]  # replace with actual 3072-dimensional vector
# index = "my_index"

# results = retrieve_similar_documents(text, example_embedding, index)
# print("Retrieved documents:", results)



# # Example usage
# text = "hello world"
# vector = get_embedding(text)
# print("Embedding vector:", vector)









