 
# Todo 

## Stock service
1. Setup frontend for viewing candlestick data:
 - echarts for viewing 
 - login using fixed username and password
 - authentication and user setup 
 - storage of subscribed symbols
 - Use advanced charts from TradingView
2. Setup buttons on frontend to view historical stock data - store 50 in database optionally
3. Auth/ whitelist to login for stock viewing
4. XGBoost for analysis
5. ARMA and Kalman filter 
6. Sentiment analysis combined with stock prediction via modal/ testing AI response on a stock for chatbot
7. Frontend dashboard - seperate into isolated views for now
8. Pushing to github and documenting read me for microservice 
9. Allow user based views - so all storage should be general but all frontend requests should use user ID / JWLP ???
10. Test pushing some data to supabase POSTGRESQL/ custom SQL command 
11. News analysis entirely in modal -> request api then use finBert for processing 

#### Subscription flow
Websocket (yes/no based on subscriber count)
Subscriptiopn Handler (number of subscriptions based on users
\+ send request to subscribe or unsubscribe to Websocket 
This is my single source of truth). Frontend requests updates to the subscription handler and processes the system stat
- Key parts of the system 
1. UserID
2. UserSubscriptions
3. Name
4. UserPassword/ credentials


## Net Worth Calculator
1. Gocardless API for banks
    1. Accessing API
    2. Setting up READ only api keys 
2. API for T212
    1. Read only API key from user
    2. User prompt 
3. API for interactive brokers
4. Alpha vantage for long term information 
5. Authentication for users to login / Encryption


### Extra tools to consider
kafka data streaming
Redis for caching of streams
Artillery/ Jmeter for analysis
Prometheus and grafana


## Company inspiirations 
perplexity ai 
simply wall street