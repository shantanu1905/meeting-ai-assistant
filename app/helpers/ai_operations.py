import requests

def get_embedding_from_service(text: str):
    url = "http://localhost:8090/embed"
    payload = {"inputs": [text]}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        embeddings = response.json().get("embeddings", [])
        if embeddings:
            return embeddings[0]  # Return first embedding if present
        raise ValueError("No embeddings returned.")
    else:
        raise ConnectionError(f"Failed to get embedding: {response.status_code}, {response.text}")









