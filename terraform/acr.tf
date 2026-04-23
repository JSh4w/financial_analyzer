resource "azurerm_container_registry" "main" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true
}

# Build and push the backend image to ACR whenever the registry is (re)created
resource "null_resource" "build_stock_service" {
  depends_on = [azurerm_container_registry.main]

  triggers = {
    acr_id = azurerm_container_registry.main.id
  }

  provisioner "local-exec" {
    command = <<-EOT
      az acr build \
        --registry ${azurerm_container_registry.main.name} \
        --image stock-service:latest \
        --file ${path.root}/../backend/stock-service/Dockerfile \
        ${path.root}/../backend/stock-service
    EOT
  }
}
