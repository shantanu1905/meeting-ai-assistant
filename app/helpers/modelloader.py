# model_loader.py
from transformers import AutoProcessor, AutoModelForSpeechSeq2Seq, pipeline

class ModelRegistry:
    whisper_processor = None
    whisper_model = None
    summarizer = None
    sentiment_analyzer = None  # ✅ Add this

    @classmethod
    def load_models(cls):
        print("📦 Loading Whisper, summarizer, and sentiment analysis models...")

        # Whisper model
        cls.whisper_processor = AutoProcessor.from_pretrained("openai/whisper-tiny")
        cls.whisper_model = AutoModelForSpeechSeq2Seq.from_pretrained("openai/whisper-tiny")
        cls.whisper_model.eval()

        # Summarization model
        cls.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

        # ✅ Sentiment analysis model
        cls.sentiment_analyzer = pipeline(
            "text-classification",
            model="tabularisai/multilingual-sentiment-analysis"
        )

        print("✅ All models loaded successfully.")