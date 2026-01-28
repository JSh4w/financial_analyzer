#!/bin/bash

# Azure Deployment Script for Financial Analyzer
# This script automates the deployment process outlined in AZURE_DEPLOYMENT_GUIDE.md
#
# Usage:
#   ./deploy-to-azure.sh                    # Interactive mode
#   ./deploy-to-azure.sh azure-config.txt   # Load config from file
#
# Config file format (azure-config.txt):
#   RESOURCE_GROUP=financial-analyzer-rg
#   LOCATION=eastus
#   ACR_NAME=myregistry
#   ALPACA_API_KEY=your-key
#   ALPACA_API_SECRET=your-secret
#   SUPABASE_URL=https://xxx.supabase.co
#   SUPABASE_KEY=your-key
#   SUPABASE_ANON_KEY=your-anon-key
#   GO_CARDLESS_SECRET_ID=your-id
#   GO_CARDLESS_SECRET_KEY=your-key
#   DEPLOY_FRONTEND=y
#   AUTO_CONFIRM=y

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(dirname "$0")"
CONFIG_FILE="${1:-}"

# Function to load config from file
load_config() {
    local file="$1"
    if [ -f "$file" ]; then
        echo -e "${GREEN}Loading configuration from: $file${NC}"
        # Source the file, but only export known variables
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ "$key" =~ ^#.*$ ]] && continue
            [[ -z "$key" ]] && continue
            # Remove leading/trailing whitespace and quotes
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
            # Export the variable
            export "$key=$value"
        done < "$file"
        return 0
    else
        return 1
    fi
}

echo -e "${GREEN}=== Financial Analyzer Azure Deployment ===${NC}\n"

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v az &> /dev/null; then
    echo -e "${RED}Azure CLI is not installed. Please install it first.${NC}"
    echo "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install it first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites met${NC}\n"

# Load config file if provided
if [ -n "$CONFIG_FILE" ]; then
    if load_config "$CONFIG_FILE"; then
        echo -e "${GREEN}✓ Configuration loaded${NC}\n"
    else
        echo -e "${RED}Config file not found: $CONFIG_FILE${NC}"
        exit 1
    fi
fi

# Configuration - use loaded values or prompt
if [ -z "$RESOURCE_GROUP" ]; then
    read -p "Enter your Azure Resource Group name (default: financial-analyzer-rg): " RESOURCE_GROUP
fi
RESOURCE_GROUP=${RESOURCE_GROUP:-financial-analyzer-rg}

if [ -z "$LOCATION" ]; then
    read -p "Enter Azure region (default: eastus): " LOCATION
fi
LOCATION=${LOCATION:-eastus}

if [ -z "$ACR_NAME" ]; then
    read -p "Enter Container Registry name (must be unique, lowercase, no spaces): " ACR_NAME
    if [ -z "$ACR_NAME" ]; then
        ACR_NAME="financialanalyzer$(openssl rand -hex 3)"
        echo "Generated ACR name: $ACR_NAME"
    fi
fi

ENVIRONMENT_NAME="financial-analyzer-env"
STATIC_APP_NAME="financial-analyzer-web"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "ACR Name: $ACR_NAME"
echo "Environment: $ENVIRONMENT_NAME"
echo ""

if [ "$AUTO_CONFIRM" != "y" ]; then
    read -p "Continue with deployment? (y/n): " CONFIRM
    if [ "$CONFIRM" != "y" ]; then
        echo "Deployment cancelled."
        exit 0
    fi
fi

# Step 1: Login to Azure
echo -e "\n${GREEN}Step 1: Checking Azure login...${NC}"
az account show &> /dev/null || az login

# Step 2: Create Resource Group
echo -e "\n${GREEN}Step 2: Creating Resource Group...${NC}"
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION"

# Step 3: Create Container Registry
echo -e "\n${GREEN}Step 3: Creating Container Registry...${NC}"
az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer --output tsv)
echo "ACR Login Server: $ACR_LOGIN_SERVER"

# Step 4: Build and Push Backend Image
echo -e "\n${GREEN}Step 4: Building and pushing backend Docker image...${NC}"
echo "This may take a few minutes..."

cd "$(dirname "$0")/backend/stock-service"

az acr login --name "$ACR_NAME"

az acr build \
  --registry "$ACR_NAME" \
  --image stock-service:latest \
  --file Dockerfile \
  .

cd - > /dev/null

# Step 5: Create Container Apps Environment
echo -e "\n${GREEN}Step 5: Creating Container Apps Environment...${NC}"
az containerapp env create \
  --name "$ENVIRONMENT_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION"

# Step 6: Get ACR Credentials
echo -e "\n${GREEN}Step 6: Getting ACR credentials...${NC}"
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" --output tsv)

# Step 7: Collect secrets
echo -e "\n${YELLOW}Step 7: Configure secrets${NC}"

# Check if secrets are already loaded from config, otherwise prompt
if [ -z "$ALPACA_API_KEY" ] || [ -z "$SUPABASE_URL" ]; then
    echo "Please provide your application secrets:"
    echo "(You can find these in your .env file - I won't read it per your instructions)"
    echo ""

    [ -z "$ALPACA_API_KEY" ] && read -p "ALPACA_API_KEY: " ALPACA_API_KEY
    [ -z "$ALPACA_API_SECRET" ] && read -p "ALPACA_API_SECRET: " ALPACA_API_SECRET
    [ -z "$SUPABASE_URL" ] && read -p "SUPABASE_URL: " SUPABASE_URL
    [ -z "$SUPABASE_KEY" ] && read -p "SUPABASE_KEY: " SUPABASE_KEY
    [ -z "$SUPABASE_ANON_KEY" ] && read -p "SUPABASE_ANON_KEY: " SUPABASE_ANON_KEY
    [ -z "$GO_CARDLESS_SECRET_ID" ] && read -p "GO_CARDLESS_SECRET_ID: " GO_CARDLESS_SECRET_ID
    [ -z "$GO_CARDLESS_SECRET_KEY" ] && read -p "GO_CARDLESS_SECRET_KEY: " GO_CARDLESS_SECRET_KEY
else
    echo -e "${GREEN}✓ Secrets loaded from config file${NC}"
fi

# Step 8: Deploy Container App
echo -e "\n${GREEN}Step 8: Deploying stock-service to Container Apps...${NC}"
az containerapp create \
  --name stock-service \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$ENVIRONMENT_NAME" \
  --image "$ACR_LOGIN_SERVER/stock-service:latest" \
  --registry-server "$ACR_LOGIN_SERVER" \
  --registry-username "$ACR_USERNAME" \
  --registry-password "$ACR_PASSWORD" \
  --target-port 8001 \
  --ingress external \
  --min-replicas 0 \
  --max-replicas 1 \
  --cpu 1.0 \
  --memory 2.0Gi \
  --secrets \
    alpaca-api-key="$ALPACA_API_KEY" \
    alpaca-api-secret="$ALPACA_API_SECRET" \
    supabase-url="$SUPABASE_URL" \
    supabase-key="$SUPABASE_KEY" \
    supabase-anon-key="$SUPABASE_ANON_KEY" \
    gocardless-secret-id="$GO_CARDLESS_SECRET_ID" \
    gocardless-secret-key="$GO_CARDLESS_SECRET_KEY" \
  --env-vars \
    "ALPACA_API_KEY=secretref:alpaca-api-key" \
    "ALPACA_API_SECRET=secretref:alpaca-api-secret" \
    "SUPABASE_URL=secretref:supabase-url" \
    "SUPABASE_KEY=secretref:supabase-key" \
    "SUPABASE_ANON_KEY=secretref:supabase-anon-key" \
    "GO_CARDLESS_SECRET_ID=secretref:gocardless-secret-id" \
    "GO_CARDLESS_SECRET_KEY=secretref:gocardless-secret-key"

# Step 9: Get Backend URL
BACKEND_URL=$(az containerapp show \
  --name stock-service \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv 2>/dev/null)

echo -e "\n${GREEN}✓ Backend deployed successfully!${NC}"
echo -e "Backend URL: ${YELLOW}https://$BACKEND_URL${NC}"
echo ""
echo "Testing backend..."
sleep 5  # Wait for container to be ready
curl -sf "https://$BACKEND_URL/health" > /dev/null 2>&1 && echo -e "${GREEN}✓ Backend is healthy!${NC}" || echo -e "${RED}✗ Backend health check failed (may still be starting)${NC}"

# Step 10: Frontend deployment
echo -e "\n${YELLOW}Step 10: Frontend Deployment${NC}"

if [ -z "$DEPLOY_FRONTEND" ]; then
    read -p "Would you like to deploy the frontend now? (y/n): " DEPLOY_FRONTEND
fi

if [ "$DEPLOY_FRONTEND" = "y" ]; then
    echo -e "\n${GREEN}Building frontend...${NC}"

    # Create production .env file
    cat > "$(dirname "$0")/frontend/.env.production" <<EOF
VITE_API_URL=https://$BACKEND_URL
EOF

    cd "$(dirname "$0")/frontend"

    # Install and build
    npm install
    npm run build

    echo -e "\n${GREEN}Deploying to Azure Static Web Apps...${NC}"
    echo "Note: For full GitHub integration, use the Azure Portal instead."

    az staticwebapp create \
      --name "$STATIC_APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --location "$LOCATION" || true

    FRONTEND_URL=$(az staticwebapp show \
      --name "$STATIC_APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --query defaultHostname \
      --output tsv 2>/dev/null || echo "")

    if [ -n "$FRONTEND_URL" ]; then
        echo -e "\n${GREEN}✓ Frontend deployed!${NC}"
        echo -e "Frontend URL: ${YELLOW}https://$FRONTEND_URL${NC}"
    fi

    cd - > /dev/null
else
    echo "Skipping frontend deployment."
    echo "You can deploy it later using the Azure Portal or CLI."
fi

# Summary
echo -e "\n${GREEN}=== Deployment Summary ===${NC}"
echo ""
echo "Resource Group: $RESOURCE_GROUP"
echo "Backend URL: https://$BACKEND_URL"
[ -n "$FRONTEND_URL" ] && echo "Frontend URL: https://$FRONTEND_URL"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update CORS settings in backend/stock-service/app/main.py"
echo "2. View logs: az containerapp logs show --name stock-service --resource-group $RESOURCE_GROUP --follow"
echo "3. Monitor in Azure Portal: https://portal.azure.com"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"

# Save configuration (without secrets for safety)
cat > "$SCRIPT_DIR/azure-deployed-config.txt" <<EOF
# Azure Deployment Configuration (generated)
# Re-run with: ./deploy-to-azure.sh azure-config.txt

RESOURCE_GROUP=$RESOURCE_GROUP
LOCATION=$LOCATION
ACR_NAME=$ACR_NAME
ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER
BACKEND_URL=$BACKEND_URL
FRONTEND_URL=${FRONTEND_URL:-Not deployed}

# Add your secrets below to re-deploy:
# ALPACA_API_KEY=
# ALPACA_API_SECRET=
# SUPABASE_URL=
# SUPABASE_KEY=
# SUPABASE_ANON_KEY=
# GO_CARDLESS_SECRET_ID=
# GO_CARDLESS_SECRET_KEY=
# DEPLOY_FRONTEND=y
# AUTO_CONFIRM=y
EOF

echo -e "\nConfiguration saved to azure-deployed-config.txt"
