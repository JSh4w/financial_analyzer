output "backend_url" {
  description = "Backend API URL"
  value       = "https://${azurerm_container_app.stock_service.ingress[0].fqdn}"
}

output "acr_login_server" {
  description = "Container Registry login server"
  value       = azurerm_container_registry.main.login_server
}

output "resource_group_name" {
  description = "Resource group name (use this when running az commands)"
  value       = azurerm_resource_group.main.name
}
