# model_loader.py
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq, pipeline

class ModelRegistry:
    whisper_processor = None
    whisper_model = None
    summarizer = None

    @classmethod
    def load_models(cls):
        print("📦 Loading Whisper and summarizer models...")
        cls.whisper_processor = AutoProcessor.from_pretrained("openai/whisper-tiny")
        cls.whisper_model = AutoModelForSpeechSeq2Seq.from_pretrained("openai/whisper-tiny")
        cls.whisper_model.eval()
        cls.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        print("✅ Models loaded.")
