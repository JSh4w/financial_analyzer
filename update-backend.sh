#!/bin/bash
# Azure Backend Update Script - Deploy latest backend to Azure Container App
# Usage: ./update-backend.sh [config-file]

set -e

CONFIG_FILE="${1:-azure-config.txt}"

# Check prerequisites
command -v az &> /dev/null || { echo "Azure CLI not installed"; exit 1; }
command -v docker &> /dev/null || { echo "Docker not installed"; exit 1; }

# Load or prompt for configuration
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo "Using config: $RESOURCE_GROUP / $ACR_NAME (from $CONFIG_FILE)"
    [ "$AUTO_CONFIRM" != "y" ] && { read -p "Continue? (y/n): " CONFIRM; [ "$CONFIRM" != "y" ] && exit 0; }
else
    echo "Config file not found: $CONFIG_FILE"
    read -p "Resource Group: " RESOURCE_GROUP
    read -p "ACR Name: " ACR_NAME
fi

# Check Azure login
az account show &> /dev/null || { echo "Not logged in. Run: az login"; exit 1; }

# Verify resources exist
az group show --name "$RESOURCE_GROUP" &> /dev/null || { echo "Resource group not found"; exit 1; }
az acr show --name "$ACR_NAME" &> /dev/null || { echo "ACR not found"; exit 1; }

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer --output tsv)

# Run tests
echo "Running tests..."
cd backend/stock-service
python -m pytest tests/ -v --tb=short || {
    read -p "Tests failed. Continue anyway? (y/n): " CONTINUE
    [ "$CONTINUE" != "y" ] && exit 1
}
cd ../..

# Build and push image
echo "Building and pushing image..."
cd backend/stock-service

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="v$TIMESTAMP"

echo "Building Docker image locally..."
docker build -t "$ACR_LOGIN_SERVER/stock-service:latest" \
             -t "$ACR_LOGIN_SERVER/stock-service:$IMAGE_TAG" \
             -f Dockerfile \
             .

echo "Logging into ACR..."
az acr login --name "$ACR_NAME"

echo "Pushing images to ACR..."
docker push "$ACR_LOGIN_SERVER/stock-service:latest"
docker push "$ACR_LOGIN_SERVER/stock-service:$IMAGE_TAG"

cd ../..

# Update container app
echo "Updating container app..."
az containerapp show --name stock-service --resource-group "$RESOURCE_GROUP" &> /dev/null || {
    echo "Container app not found"; exit 1;
}

az containerapp update \
  --name stock-service \
  --resource-group "$RESOURCE_GROUP" \
  --image "$ACR_LOGIN_SERVER/stock-service:latest"

# Get backend URL
BACKEND_URL=$(az containerapp show \
  --name stock-service \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv 2>/dev/null)

# Health check
echo "Checking health..."
sleep 10

for i in {1..10}; do
    if curl -sf "https://$BACKEND_URL/health" > /dev/null 2>&1; then
        echo "Backend healthy!"
        break
    fi
    [ $i -eq 10 ] && { echo "Health check failed"; exit 1; }
    sleep 5
done

# Save config
cat > azure-config.txt <<EOF
RESOURCE_GROUP="$RESOURCE_GROUP"
LOCATION="${LOCATION:-westeurope}"
ACR_NAME="$ACR_NAME"
ACR_LOGIN_SERVER="$ACR_LOGIN_SERVER"
BACKEND_URL="$BACKEND_URL"
LAST_DEPLOYMENT="$TIMESTAMP"
LAST_IMAGE_TAG="$IMAGE_TAG"
EOF

echo "Deployment complete!"
echo "Backend URL: https://$BACKEND_URL"
echo "Image: $IMAGE_TAG"
