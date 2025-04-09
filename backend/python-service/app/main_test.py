# backend/python-service/app/main_test.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

# Import your actual app creation logic, but configure it for testing
app = FastAPI(
    title="Financial Analysis Service (Test Mode)",
    description="Python service for financial data analysis - Test Environment",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Financial Analysis Service API - Test Mode"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "environment": "test"}

# Special test-only endpoints can be added here
@app.get("/test/reset")
def reset_test_data():
    """Endpoint to reset test data between test runs"""
    # You can add logic here to reset any test databases or state
    return {"message": "Test data reset successfully"}

# Create a test client
client = TestClient(app)

# This allows running the file directly for testing
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main_test:app", host="0.0.0.0", port=5000, reload=True)