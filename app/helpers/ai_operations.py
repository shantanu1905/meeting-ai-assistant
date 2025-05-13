import json
import requests
from app.helpers.constants import EMBEDDING_URL , RETRIVER_URL , OLLAMA_URL

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


# 4) Putting it all together



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









