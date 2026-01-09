# Azure Deployment Guide

This guide will walk you through deploying your Financial Analyzer application to Microsoft Azure.

## Architecture Overview

- **Backend**: stock-service (FastAPI) → Azure Container Apps
- **Frontend**: React/Vite → Azure Static Web Apps

## Prerequisites

Before starting, you'll need:
- Azure account (free tier works for testing)
- Azure CLI installed
- Docker installed locally
- Your application environment variables

## Part 1: Install and Setup Azure CLI

### Step 1: Install Azure CLI

If you don't have Azure CLI installed, install it:

```bash
# For Linux/WSL
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# For macOS
brew install azure-cli

# For Windows
# Download from: https://aka.ms/installazurecliwindows
```

Verify installation:
```bashaz l
az --version
```

### Step 2: Login to Azure

```bash
az login
```

This will open a browser window for authentication. Follow the prompts to sign in.

### Step 3: Set your subscription (if you have multiple)

```bash
# List all subscriptions
az account list --output table

# Set the subscription you want to use
az account set --subscription "YOUR_SUBSCRIPTION_NAME_OR_ID"
```

## Part 2: Create Azure Resources

### Step 4: Create a Resource Group

A resource group is a container that holds related resources.

```bash
# Choose a region close to your users (examples: eastus, westeurope, southeastasia)
RESOURCE_GROUP="financial-analyzer-rg"
LOCATION="eastus"

az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 5: Create Azure Container Registry (ACR)

ACR stores your Docker images. Think of it as your private Docker Hub.

```bash
# Name must be globally unique and contain only lowercase letters and numbers
ACR_NAME="financialanalyzer$(openssl rand -hex 3)"

az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# If this fails try 
az provider show -n Microsoft.ContainerRegistry --query "registrationState" -o tsv

# If it shows "Registering"
# wait 1-2 minutes until it shows "Registered"
# If it isn't registered try 
# "az provider register --namespace Microsoft.ContainerRegistry"


# Save the login server for later
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer --output tsv)
echo "Your ACR login server: $ACR_LOGIN_SERVER"
```

**Why admin-enabled?** This allows Container Apps to pull images using admin credentials (simpler for getting started).

### Step 6: Build and Push Backend Docker Image

Navigate to your backend directory and build the image:

```bash
cd /workspaces/financial_analyzer/backend/stock-service

# Login to your container registry
az acr login --name $ACR_NAME

# Build and push the image directly to ACR
az acr build \
  --registry $ACR_NAME \
  --image stock-service:latest \
  --file Dockerfile \
  .
#If this failed try running 
az provider register -n Microsoft.OperationalInsights --wait
# This will mean we can have a Log Analytics workspace, only needs to be ran once per account
```

ACR Tasks may be blocked on free/student accounts. 
If so Build Locally and push instead
```bash
az acr login --name $ACR_NAME

ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME \
--query loginServer --output tsv)

docker build -t  $ACR_LOGIN_SERVER/stock-service:latest -f Dockerfile .

docker push $ACR_LOGIN_SERVER/stock-service:latest
```


**What's happening?** Azure builds your Docker image in the cloud and pushes it to your container registry.

## Part 3: Deploy Backend to Azure Container Apps

### Step 7: Create Container Apps Environment

The environment is a secure boundary around your container apps.

```bash
ENVIRONMENT_NAME="financial-analyzer-env"

az containerapp env create \
  --name $ENVIRONMENT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 8: Get ACR Credentials

```bash
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv)
```

### Step 9: Deploy stock-service Container App

Before running this, you'll need to know your environment variables. Check your `.env.example` file.

Replace "YOUR" with the actual values from your .env file

min-replicas is 0 so it can scale down to no servers
max-replicas is 1 for now; we can't scale horizontally without redis and or microservices

```bash
az containerapp create \
    --name stock-service \
    --resource-group $RESOURCE_GROUP \
    --environment $ENVIRONMENT_NAME \
    --image $ACR_LOGIN_SERVER/stock-service:latest \
    --registry-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_USERNAME \
    --registry-password $ACR_PASSWORD \
    --target-port 8001 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 1 \
    --cpu 1.0 \
    --memory 2.0Gi \
    --secrets \
      finnhub-api-key="REPLACE" \
      finnhub-base-url="https://finnhub.io/api/v1/" \
      alpaca-test-url="wss://stream.data.alpaca.markets/v2/test" \
      alpaca-api-key="REPLACE" \
      alpaca-api-secret="REPLACE" \
      alpha-vantage-api-key="REPLACE" \
      supabase-jwks-url="REPLACE" \
      supabase-jwt-secret="REPLACE" \
      supabase-url="REPLACE" \
      supabase-key="REPLACE" \
      modal-token-id="REPLACE" \
      modal-token-secret="REPLACE" \
      gocardless-secret-key="REPLACE" \
      gocardless-secret-id="REPLACE" \
      bank-encryption-key="REPLACE" \
    --env-vars \
      "FINNHUB_API_KEY=secretref:finnhub-api-key" \
      "FINNHUB_BASE_URL=secretref:finnhub-base-url" \
      "ALPACA_TEST_URL=secretref:alpaca-test-url" \
      "ALPACA_API_KEY=secretref:alpaca-api-key" \
      "ALPACA_API_SECRET=secretref:alpaca-api-secret" \
      "ALPHA_VANTAGE_API_KEY=secretref:alpha-vantage-api-key" \
      "SUPABASE_JWKS_URL=secretref:supabase-jwks-url" \
      "SUPABASE_JWT_SECRET=secretref:supabase-jwt-secret" \
      "SUPABASE_URL=secretref:supabase-url" \
      "SUPABASE_KEY=secretref:supabase-key" \
      "MODAL_TOKEN_ID=secretref:modal-token-id" \
      "MODAL_TOKEN_SECRET=secretref:modal-token-secret" \
      "GO_CARDLESS_SECRET_KEY=secretref:gocardless-secret-key" \
      "GO_CARDLESS_SECRET_ID=secretref:gocardless-secret-id" \
      "BANK_ENCRYPTION_KEY=secretref:bank-encryption-key"
```

### Step 10: Get Backend URL

```bash
BACKEND_URL=$(az containerapp show \
  --name stock-service \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn \
  --output tsv)

echo "Your backend is live at: https://$BACKEND_URL"
```

**Test it:**
```bash
curl https://$BACKEND_URL/health
```

You should see: `{"status":"healthy","service":"stock-service","environment":"production"}`

## Part 4: Deploy Frontend to Azure Static Web Apps

### Step 11: Update Frontend API Endpoint

Your frontend needs to know where your backend is deployed. Update your frontend `.env` or config:

Create/update `/workspaces/financial_analyzer/frontend/.env.production`:
```env
VITE_API_URL=https://$BACKEND_URL
```

### Step 12: Build Frontend

```bash
cd /workspaces/financial_analyzer/frontend

# Install dependencies (if not already done)
npm install

# Build for production
npm run build
```

This creates an optimized production build in the `dist/` directory.

### Step 13: Deploy to Azure Static Web Apps

```bash
STATIC_APP_NAME="lucrum-stack-web"

# Create the static web app
az staticwebapp create \
  --name $STATIC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --source ./dist \
  --location $LOCATION \
  --branch main \
  --app-location "/" \
  --output-location "dist"
```

Alternatively, use the Azure portal for easier GitHub integration:

1. Go to Azure Portal → Static Web Apps → Create
2. Connect your GitHub repository
3. Select framework: React
4. Build settings:
   - App location: `/frontend`
   - Output location: `dist`

### Step 14: Get Frontend URL

```bash
FRONTEND_URL=$(az staticwebapp show \
  --name $STATIC_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query defaultHostname \
  --output tsv)

echo "Your frontend is live at: https://$FRONTEND_URL"
```

## Part 5: Configure CORS (Important!)

Your backend needs to allow requests from your frontend domain.

### Step 15: Update Backend CORS Settings

You'll need to modify your FastAPI CORS middleware to include your production frontend URL.

In `backend/stock-service/app/main.py`, update the CORS middleware:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local development
        "https://YOUR_FRONTEND_URL",  # Production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Then rebuild and redeploy:

```bash
cd /workspaces/financial_analyzer/backend/stock-service

az acr build \
  --registry $ACR_NAME \
  --image stock-service:latest \
  --file Dockerfile \
  .

# Container Apps will automatically pull the new image
az containerapp update \
  --name stock-service \
  --resource-group $RESOURCE_GROUP
```

## Part 6: Monitoring and Logs

### View Backend Logs

```bash
# Stream logs in real-time
az containerapp logs show \
  --name stock-service \
  --resource-group $RESOURCE_GROUP \
  --follow

# Or view in Azure Portal
# Container Apps → stock-service → Log stream
```

### View Frontend Logs

```bash
# View deployment logs
az staticwebapp show \
  --name $STATIC_APP_NAME \
  --resource-group $RESOURCE_GROUP
```

## Part 7: Continuous Deployment (Optional)

### For Backend (GitHub Actions)

Create `.github/workflows/deploy-backend.yml`:

```yaml
name: Deploy Backend to Azure

on:
  push:
    branches: [main]
    paths:
      - 'backend/stock-service/**'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Login to Azure
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and push image
        run: |
          az acr build \
            --registry ${{ secrets.ACR_NAME }} \
            --image stock-service:${{ github.sha }} \
            --image stock-service:latest \
            --file backend/stock-service/Dockerfile \
            backend/stock-service

      - name: Deploy to Container Apps
        run: |
          az containerapp update \
            --name stock-service \
            --resource-group ${{ secrets.RESOURCE_GROUP }} \
            --image ${{ secrets.ACR_LOGIN_SERVER }}/stock-service:${{ github.sha }}
```

### For Frontend

Azure Static Web Apps automatically deploys from GitHub when you connect your repository.

## Cost Estimation

### Free Tier Limits
- **Container Apps**: 180,000 vCPU-seconds, 360,000 GiB-seconds per month
- **Static Web Apps**: 100 GB bandwidth, unlimited static content
- **Container Registry**: 10 GB storage

For a small application with moderate traffic, you can likely stay in the free tier.

## Troubleshooting

### Backend not responding
1. Check logs: `az containerapp logs show --name stock-service --resource-group $RESOURCE_GROUP --follow`
2. Verify secrets are set correctly
3. Check ingress is set to "external"

### Frontend can't reach backend
1. Verify CORS settings in backend
2. Check backend URL in frontend .env.production
3. Ensure backend health endpoint works

### Container fails to start
1. Test Docker image locally first
2. Check environment variables match your .env.example
3. Review startup logs in Azure Portal

## Useful Commands

```bash
# Restart container app
az containerapp revision restart \
  --name stock-service \
  --resource-group $RESOURCE_GROUP

# Scale manually
az containerapp update \
  --name stock-service \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 2 \
  --max-replicas 5

# Delete everything (when done testing)
az group delete --name $RESOURCE_GROUP --yes
```

## Next Steps

1. Set up custom domain names
2. Configure Azure Front Door for CDN
3. Set up Application Insights for monitoring
4. Configure auto-scaling rules
5. Set up staging environments
6. Configure backup and disaster recovery

## Resources

- [Azure Container Apps Docs](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Static Web Apps Docs](https://learn.microsoft.com/en-us/azure/static-web-apps/)
- [Azure CLI Reference](https://learn.microsoft.com/en-us/cli/azure/)
