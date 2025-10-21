"""FinBERT sentiment analysis using Modal GPU infrastructure
This module provides serverless GPU-accelerated sentiment analysis for financial news
"""
import modal
from typing import List, Dict, Any

# Create Modal app
app = modal.App("finbert-sentiment-analysis")

# Define the Modal image with all necessary dependencies
# The model will be downloaded during container startup
finbert_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.0.0",
        "transformers>=4.30.0",
        "scipy>=1.10.0",
    )
)


@app.cls(
    gpu="T4",  # T4 GPU is cost-effective for inference (~$0.60/hour)
    image=finbert_image,
    timeout=180,  # 3 minute timeout
    scaledown_window=120,  # Keep container warm for 2 minutes
)
class FinBERTAnalyzer:
    """GPU-accelerated FinBERT sentiment analyzer"""

    @modal.enter()
    def load_model(self):
        """Load model when container starts (runs once per container)"""
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification

        print("Loading FinBERT model...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        model_name = "ProsusAI/finbert"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()  # Set to evaluation mode

        print("FinBERT model loaded successfully!")

    @modal.method()
    def analyze_sentiment(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for a batch of texts

        Args:
            texts: List of text strings to analyze (e.g., news headlines/articles)

        Returns:
            List of sentiment results with label and scores
            Format: [{"label": "positive/negative/neutral", "score": 0.95, "scores": {...}}, ...]
        """
        import time 
        import torch
        import torch.nn.functional as F
        start_time = time.perf_counter()
        if not texts:
            return []

        print(f"Analyzing sentiment for {len(texts)} texts...")

        results = []

        # Process in batches for efficiency (adjust batch_size based on GPU memory)
        batch_size = 8

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            # Tokenize
            inputs = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            ).to(self.device)

            # Inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = F.softmax(outputs.logits, dim=-1)

            # Convert to CPU and process results
            predictions_cpu = predictions.cpu().numpy()

            for pred in predictions_cpu:
                # FinBERT labels: 0=positive, 1=negative, 2=neutral
                label_map = {0: "positive", 1: "negative", 2: "neutral"}
                label_idx = pred.argmax()

                result = {
                    "label": label_map[label_idx],
                    "score": float(pred[label_idx]),
                    "scores": {
                        "positive": float(pred[0]),
                        "negative": float(pred[1]),
                        "neutral": float(pred[2])
                    }
                }
                results.append(result)

        print(f"Sentiment analysis complete: {len(results)} results")
        total_time = time.perf_counter() - start_time 
        print(f"GPU time = {total_time}")
        return results


# # Web endpoint for HTTP access (optional - useful for testing)
# @app.function(image=finbert_image)
# @modal.fastapi_endpoint(method="POST")
# def analyze_sentiment_http(data: Dict[str, Any]) -> Dict[str, Any]:
#     """
#     HTTP endpoint for sentiment analysis

#     POST body format:
#     {
#         "texts": ["Article text 1", "Article text 2", ...]
#     }

#     Returns:
#     {
#         "results": [...],
#         "count": 2
#     }
#     """
#     texts = data.get("texts", [])

#     if not texts:
#         return {"error": "No texts provided", "count": 0, "results": []}

#     # Call the class method
#     analyzer = FinBERTAnalyzer()
#     results = analyzer.analyze_sentiment.remote(texts)

#     return {
#         "results": results,
#         "count": len(results)
#     }


# Local test entrypoint
@app.local_entrypoint()
def main():
    """Test the FinBERT analyzer with sample financial news"""
    import time 
    start = time.perf_counter()
    # Sample financial news for testing
    test_texts = [
        "Apple stock surges to all-time high on strong earnings beat",
        "Tech sector faces headwinds as regulatory concerns mount",
        "Federal Reserve maintains interest rates at current levels",
        "Tesla announces major expansion plans in European markets",
        "Banking sector shows signs of weakness amid economic uncertainty"
    ]

    print("=" * 60)
    print("Testing FinBERT Sentiment Analysis on Modal")
    print("=" * 60)
    print(f"\nAnalyzing {len(test_texts)} sample news articles...\n")

    # Run analysis
    analyzer = FinBERTAnalyzer()
    results = analyzer.analyze_sentiment.remote(test_texts)

    # Display results
    for i, (text, result) in enumerate(zip(test_texts, results), 1):
        print(f"\n{i}. Text: {text[:80]}...")
        print(f"   Sentiment: {result['label'].upper()} ({result['score']:.2%} confidence)")
        print(f"   Scores: Positive={result['scores']['positive']:.2%}, "
              f"Negative={result['scores']['negative']:.2%}, "
              f"Neutral={result['scores']['neutral']:.2%}")

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
    tot = time.perf_counter() - start
    print(f"All time = {tot}")

if __name__ == "__main__":
    main()