# ML Prediction System Plan - FinBERT Integration

## Overview

Build a sentiment-driven stock prediction system using:
- **FinBERT**: Financial sentiment analysis from news/social media
- **Your live market data**: Real-time price/volume from Alpaca
- **Historical data**: DuckDB storage for training
- **Modal**: Serverless deployment for ML inference

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  DATA SOURCES                                               │
├─────────────────────────────────────────────────────────────┤
│  1. Market Data (Alpaca WebSocket)                          │
│     - Real-time trades, quotes, bars                        │
│     - Store in DuckDB                                       │
│                                                             │
│  2. Financial News (New WebSocket/API)                      │
│     - Alpaca News API                                       │
│     - OR NewsAPI / Benzinga / Alpha Vantage                 │
│     - Store headlines + timestamps                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  FEATURE ENGINEERING                                        │
├─────────────────────────────────────────────────────────────┤
│  Technical Features (from market data):                     │
│    - Price momentum (returns over 1hr, 1day, 1week)        │
│    - Volume trends                                          │
│    - Moving averages (MA5, MA20, MA50)                     │
│    - RSI, MACD, Bollinger Bands                            │
│                                                             │
│  Sentiment Features (from FinBERT):                         │
│    - News sentiment score (-1 to +1)                        │
│    - Sentiment trend (last 1hr, 6hr, 24hr)                 │
│    - News volume (# of articles)                            │
│    - Entity mentions (company name frequency)               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  ML MODEL (Modal)                                           │
├─────────────────────────────────────────────────────────────┤
│  Input: Technical features + Sentiment features             │
│  Model: RandomForest / XGBoost / LSTM                       │
│  Output:                                                    │
│    - Prediction: UP/DOWN/NEUTRAL                            │
│    - Confidence: 0-100%                                     │
│    - Price target (optional)                                │
│    - Risk score                                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND DISPLAY                                           │
├─────────────────────────────────────────────────────────────┤
│  - Overlay predictions on TradingView charts                │
│  - Show sentiment gauge                                     │
│  - Display recent news with sentiment                       │
│  - Signal confidence indicator                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: News Data Integration (Week 1)

### 1.1 Choose News Source

**Option A: Alpaca News API** (Recommended - already integrated)
```python
# Alpaca provides news WebSocket feed
# wss://stream.data.alpaca.markets/v1beta1/news
```

**Option B: NewsAPI** (Free tier: 100 requests/day)
```python
# REST API polling
# https://newsapi.org/v2/everything?q=AAPL&apiKey=...
```

**Option C: Alpha Vantage News Sentiment** (Free tier: 25 requests/day)
```python
# Includes pre-computed sentiment!
# https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers=AAPL
```

### 1.2 Add News WebSocket Manager

Create `backend/stock-service/app/stocks/news_websocket_manager.py`:

```python
class NewsWebSocketManager:
    """Manages news WebSocket connections similar to market data"""

    def __init__(self, uri, output_queue):
        # Similar structure to WebSocketManager
        # Subscribe to news for specific symbols
        pass

    async def subscribe_news(self, symbol: str):
        """Subscribe to news for a symbol"""
        pass
```

### 1.3 Store News Data

Add news table to DuckDB:

```sql
CREATE TABLE news (
    id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    headline TEXT NOT NULL,
    summary TEXT,
    source VARCHAR,
    url VARCHAR,
    published_at TIMESTAMP NOT NULL,
    sentiment_score DOUBLE,  -- FinBERT output
    sentiment_label VARCHAR, -- positive/negative/neutral
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_news_symbol_time ON news (symbol, published_at DESC);
```

### 1.4 Deliverables
- [ ] News WebSocket/API integration working
- [ ] News stored in DuckDB
- [ ] Backend endpoint: `GET /news/{symbol}?hours=24`

---

## Phase 2: FinBERT Sentiment Analysis (Week 1-2)

### 2.1 FinBERT Setup

**Model:** `ProsusAI/finbert` (Hugging Face)

```python
# Install dependencies
pip install transformers torch

# Load FinBERT
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

def analyze_sentiment(text: str) -> dict:
    """
    Returns:
        {
            'label': 'positive' | 'negative' | 'neutral',
            'score': 0.95,  # confidence
            'sentiment_value': 0.85  # -1 to +1 scale
        }
    """
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    outputs = model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

    labels = ['positive', 'negative', 'neutral']
    scores = probs[0].tolist()

    max_idx = scores.index(max(scores))
    return {
        'label': labels[max_idx],
        'score': scores[max_idx],
        'sentiment_value': scores[0] - scores[1]  # positive - negative
    }
```

### 2.2 Sentiment Processing Pipeline

Create `backend/stock-service/app/ml/sentiment_analyzer.py`:

```python
class SentimentAnalyzer:
    """Analyzes news sentiment using FinBERT"""

    def __init__(self):
        self.model = load_finbert()
        self.db_manager = DuckDBManager()

    async def process_news_item(self, news_item: dict):
        """Process single news item and store sentiment"""
        sentiment = analyze_sentiment(news_item['headline'] + " " + news_item['summary'])

        # Update news table with sentiment
        self.db_manager.update_news_sentiment(
            news_id=news_item['id'],
            sentiment_score=sentiment['sentiment_value'],
            sentiment_label=sentiment['label']
        )

    async def get_aggregated_sentiment(self, symbol: str, hours: int = 24) -> dict:
        """Get aggregated sentiment for a symbol over time window"""
        news = self.db_manager.get_recent_news(symbol, hours)

        if not news:
            return {'sentiment': 0, 'confidence': 0, 'count': 0}

        sentiments = [n['sentiment_score'] for n in news]

        return {
            'sentiment': np.mean(sentiments),
            'confidence': np.std(sentiments),  # lower = more consistent
            'count': len(news),
            'trend': sentiments[-5:],  # last 5 articles
            'positive_ratio': sum(1 for s in sentiments if s > 0.3) / len(sentiments)
        }
```

### 2.3 Background Processing

Add sentiment analysis task:

```python
# In main.py startup
asyncio.create_task(sentiment_analyzer.process_news_queue())
```

### 2.4 Deliverables
- [ ] FinBERT loaded and running
- [ ] News sentiment stored in DuckDB
- [ ] Backend endpoint: `GET /sentiment/{symbol}`
- [ ] Real-time sentiment updates

---

## Phase 3: Feature Engineering (Week 2)

### 3.1 Technical Features

Create `backend/stock-service/app/ml/feature_engineering.py`:

```python
def calculate_technical_features(symbol: str, lookback_hours: int = 168) -> pd.DataFrame:
    """
    Extract technical features from OHLCV data

    Returns DataFrame with features:
        - returns_1h, returns_24h, returns_7d
        - ma_5, ma_20, ma_50
        - rsi_14
        - macd, macd_signal
        - volume_ratio (current vs avg)
        - volatility
    """
    # Get historical data from DuckDB
    candles = db_manager.get_candles_range(symbol, start, end)
    df = pd.DataFrame(candles).T

    # Calculate features
    df['returns_1h'] = df['close'].pct_change(periods=60)
    df['returns_24h'] = df['close'].pct_change(periods=1440)
    df['ma_5'] = df['close'].rolling(5).mean()
    df['ma_20'] = df['close'].rolling(20).mean()
    df['rsi_14'] = calculate_rsi(df['close'], 14)

    return df
```

### 3.2 Sentiment Features

```python
def calculate_sentiment_features(symbol: str) -> dict:
    """
    Extract sentiment features

    Returns:
        - sentiment_1h: avg sentiment last 1 hour
        - sentiment_6h: avg sentiment last 6 hours
        - sentiment_24h: avg sentiment last 24 hours
        - sentiment_trend: positive/negative momentum
        - news_volume: # of articles last 24h
    """
    sentiment_data = sentiment_analyzer.get_aggregated_sentiment(symbol, hours=24)

    return {
        'sentiment_current': sentiment_data['sentiment'],
        'sentiment_confidence': sentiment_data['confidence'],
        'news_volume_24h': sentiment_data['count'],
        'positive_ratio': sentiment_data['positive_ratio']
    }
```

### 3.3 Combined Features

```python
def create_prediction_features(symbol: str) -> pd.DataFrame:
    """Combine technical + sentiment features for ML model"""

    technical = calculate_technical_features(symbol)
    sentiment = calculate_sentiment_features(symbol)

    # Merge into single feature set
    features = technical.join(pd.DataFrame([sentiment]))

    return features
```

### 3.4 Deliverables
- [ ] Technical indicators calculated
- [ ] Sentiment features extracted
- [ ] Combined feature dataset ready for ML
- [ ] Backend endpoint: `GET /features/{symbol}`

---

## Phase 4: ML Model Training (Week 3)

### 4.1 Training Data Preparation

```python
# Create training dataset
def prepare_training_data(symbols: List[str], days: int = 90):
    """
    For each symbol:
        - Get historical features (technical + sentiment)
        - Label: Did price go up/down in next X hours?
        - Create train/test split
    """

    X = []  # Features
    y = []  # Labels (1 = up, 0 = down)

    for symbol in symbols:
        features = create_prediction_features(symbol)

        # Label: 1 if price increased 1% in next 24h
        features['target'] = (features['close'].shift(-1440) > features['close'] * 1.01).astype(int)

        X.append(features.drop('target', axis=1))
        y.append(features['target'])

    return train_test_split(X, y, test_size=0.2)
```

### 4.2 Model Selection

**Start Simple:**
```python
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42
)

model.fit(X_train, y_train)
```

**Or Use XGBoost:**
```python
import xgboost as xgb

model = xgb.XGBClassifier(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5
)

model.fit(X_train, y_train)
```

### 4.3 Model Evaluation

```python
# Evaluate
y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)

print(f"Accuracy: {accuracy_score(y_test, y_pred)}")
print(f"Precision: {precision_score(y_test, y_pred)}")
print(f"Recall: {recall_score(y_test, y_pred)}")

# Feature importance
feature_importance = pd.DataFrame({
    'feature': X_train.columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
```

### 4.4 Deliverables
- [ ] Training pipeline working
- [ ] Model trained on historical data
- [ ] Model evaluation metrics documented
- [ ] Model saved (pickle/joblib)

---

## Phase 5: Modal Deployment (Week 3-4)

### 5.1 Modal Setup

```python
# modal_app.py
import modal

stub = modal.Stub("stock-predictor")

# Define Modal image with dependencies
image = modal.Image.debian_slim().pip_install(
    "transformers",
    "torch",
    "pandas",
    "scikit-learn",
    "xgboost"
)

# Mount trained model
model_volume = modal.Volume.from_name("stock-models")

@stub.function(
    image=image,
    volumes={"/models": model_volume},
    cpu=2,
    memory=4096
)
def predict(symbol: str, features: dict) -> dict:
    """
    Run prediction on Modal

    Input: symbol + current features
    Output: prediction + confidence
    """
    import joblib

    model = joblib.load("/models/stock_predictor.pkl")

    # Convert features to model format
    X = prepare_features(features)

    # Predict
    prediction = model.predict(X)[0]
    confidence = model.predict_proba(X)[0].max()

    return {
        'symbol': symbol,
        'prediction': 'UP' if prediction == 1 else 'DOWN',
        'confidence': float(confidence),
        'timestamp': datetime.now().isoformat()
    }

@stub.function(image=image)
async def batch_predict(symbols: List[str]) -> List[dict]:
    """Run predictions for multiple symbols"""
    results = []
    for symbol in symbols:
        features = await fetch_features(symbol)
        pred = predict.call(symbol, features)
        results.append(pred)
    return results
```

### 5.2 FastAPI Integration

```python
# In main.py
import modal

modal_stub = modal.Stub.lookup("stock-predictor")
predict_fn = modal.Function.lookup("stock-predictor", "predict")

@app.get("/predict/{symbol}")
async def get_prediction(symbol: str):
    """Get ML prediction for a symbol"""

    # Get current features
    features = create_prediction_features(symbol)

    # Call Modal function
    prediction = predict_fn.call(symbol, features.to_dict())

    # Also get sentiment context
    sentiment = sentiment_analyzer.get_aggregated_sentiment(symbol)

    return {
        **prediction,
        'sentiment': sentiment,
        'features': features.iloc[-1].to_dict()
    }
```

### 5.3 Deliverables
- [ ] Model deployed to Modal
- [ ] FastAPI endpoint calls Modal
- [ ] Predictions returned < 1 second
- [ ] Backend endpoint: `GET /predict/{symbol}`

---

## Phase 6: Frontend Display (Week 4)

### 6.1 Prediction Overlay on Charts

```tsx
// Add prediction indicator component
interface PredictionDisplayProps {
  prediction: {
    prediction: 'UP' | 'DOWN' | 'NEUTRAL';
    confidence: number;
    sentiment: number;
  };
}

const PredictionDisplay: React.FC<PredictionDisplayProps> = ({ prediction }) => {
  return (
    <div style={{
      position: 'absolute',
      top: 20,
      right: 20,
      background: 'rgba(0,0,0,0.8)',
      padding: '15px',
      borderRadius: '8px',
      border: `2px solid ${prediction.prediction === 'UP' ? '#4CAF50' : '#f44336'}`
    }}>
      <h3>AI Prediction</h3>
      <div style={{ fontSize: '24px', fontWeight: 'bold', color: prediction.prediction === 'UP' ? '#4CAF50' : '#f44336' }}>
        {prediction.prediction === 'UP' ? '↑' : '↓'} {prediction.prediction}
      </div>
      <div>Confidence: {(prediction.confidence * 100).toFixed(1)}%</div>
      <div>Sentiment: {prediction.sentiment > 0 ? '😊' : '😞'} {prediction.sentiment.toFixed(2)}</div>
    </div>
  );
};
```

### 6.2 Recent News Display

```tsx
const NewsPanel: React.FC<{ symbol: string }> = ({ symbol }) => {
  const [news, setNews] = useState([]);

  useEffect(() => {
    fetch(`http://localhost:8001/news/${symbol}?hours=24`)
      .then(res => res.json())
      .then(setNews);
  }, [symbol]);

  return (
    <div className="news-panel">
      <h3>Recent News</h3>
      {news.map(item => (
        <div key={item.id} className={`news-item sentiment-${item.sentiment_label}`}>
          <div className="headline">{item.headline}</div>
          <div className="sentiment">
            Sentiment: {item.sentiment_score > 0 ? '📈' : '📉'}
            {(item.sentiment_score * 100).toFixed(0)}%
          </div>
        </div>
      ))}
    </div>
  );
};
```

### 6.3 Deliverables
- [ ] Prediction overlay on charts
- [ ] Sentiment gauge/indicator
- [ ] Recent news with sentiment
- [ ] Auto-refresh predictions every N minutes

---

## Success Metrics

### Model Performance
- **Accuracy**: >55% (better than random)
- **Precision**: >60% (when it says UP, it's usually right)
- **Sharpe Ratio**: >1.0 (if used for trading)

### System Performance
- **Prediction latency**: <1 second
- **News processing**: <5 seconds after publish
- **Sentiment analysis**: <500ms per article

### User Experience
- **Clear signals**: UP/DOWN with confidence
- **Context**: Show why (sentiment + technicals)
- **Accuracy tracking**: Display historical win rate

---

## Timeline Summary

| Week | Focus | Deliverable |
|------|-------|-------------|
| **1** | News integration | News stored, displayed |
| **1-2** | FinBERT setup | Sentiment analysis working |
| **2** | Feature engineering | Technical + sentiment features |
| **3** | Model training | Trained model with metrics |
| **3-4** | Modal deployment | API endpoint returning predictions |
| **4** | Frontend | Predictions overlaid on charts |

**Total: 4 weeks to MVP**

---

## Future Enhancements

1. **Multi-timeframe predictions** (1hr, 4hr, 1day, 1week)
2. **Ensemble models** (combine multiple models)
3. **Risk assessment** (volatility prediction)
4. **Backtesting** (how would it have performed historically)
5. **Auto-trading** (execute based on high-confidence signals)
6. **Explainability** (SHAP values - why this prediction?)

---

## Questions to Address

1. **Which symbols to train on?** (Start with liquid stocks: AAPL, TSLA, MSFT, NVDA)
2. **Prediction timeframe?** (Next 1hr? 24hr? 1 week?)
3. **Risk tolerance?** (High confidence only, or all signals?)
4. **Modal budget?** (Modal has free tier, then pay-as-you-go)

---

## Next Steps

**Ready to start? Here's what to do next:**

1. ✅ **Choose news source** (Recommend: Alpaca News API)
2. ✅ **Set up DuckDB news table**
3. ✅ **Integrate news WebSocket/API**
4. ✅ **Test FinBERT locally** (run sentiment on sample headlines)

**Want me to start implementing Phase 1?** 🚀
