#!/bin/bash
# Azure Container App Status - View configuration and health
# Usage: ./azure-status.sh [config-file]

CONFIG_FILE="${1:-azure-config.txt}"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config file not found: $CONFIG_FILE"
    exit 1
fi

source "$CONFIG_FILE"

echo "=== Azure Container App Status ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "Container App: stock-service"
echo ""

# Check Azure login
az account show &> /dev/null || { echo "Not logged in. Run: az login"; exit 1; }

echo "--- Scaling Configuration ---"
az containerapp show \
  --name stock-service \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.template.scale" \
  --output table 2>/dev/null || echo "Failed to get scaling config"

echo ""
echo "--- Ingress Configuration ---"
az containerapp show \
  --name stock-service \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.{FQDN:fqdn,Port:targetPort,External:external,Transport:transport}" \
  --output table 2>/dev/null || echo "Failed to get ingress config"

echo ""
echo "--- Current Replicas ---"
az containerapp replica list \
  --name stock-service \
  --resource-group "$RESOURCE_GROUP" \
  --query "[].{Name:name,Created:properties.createdTime,State:properties.runningState}" \
  --output table 2>/dev/null || echo "No replicas running (scaled to 0)"

echo ""
echo "--- Health Check ---"
BACKEND_URL=$(az containerapp show \
  --name stock-service \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" \
  --output tsv 2>/dev/null)

if [ -n "$BACKEND_URL" ]; then
    if curl -sf "https://$BACKEND_URL/health" > /dev/null 2>&1; then
        echo "✓ Backend healthy: https://$BACKEND_URL"
    else
        echo "✗ Backend not responding (may be scaled to 0)"
        echo "  URL: https://$BACKEND_URL"
    fi
fi

echo ""
echo "--- Recent Logs (last 50 lines) ---"
echo "Run: az containerapp logs show --name stock-service --resource-group $RESOURCE_GROUP --tail 50"
