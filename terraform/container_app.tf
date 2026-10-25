resource "azurerm_log_analytics_workspace" "main" {
  name                = "financial-analyzer-logs"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "main" {
  name                       = "financial-analyzer-env"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
}

resource "azurerm_container_app" "stock_service" {
  name                         = "stock-service"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  depends_on = [null_resource.build_stock_service]

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }
  secret {
    name  = "alpaca-api-key"
    value = var.alpaca_api_key
  }
  secret {
    name  = "alpaca-api-secret"
    value = var.alpaca_api_secret
  }
  secret {
    name  = "supabase-url"
    value = var.supabase_url
  }
  secret {
    name  = "supabase-key"
    value = var.supabase_key
  }
  secret {
    name  = "gocardless-secret-id"
    value = var.gocardless_secret_id
  }
  secret {
    name  = "gocardless-secret-key"
    value = var.gocardless_secret_key
  }
  secret {
    name  = "bank-encryption-key"
    value = var.bank_encryption_key
  }
  secret {
    name  = "snaptrade-client-id"
    value = var.snaptrade_client_id
  }
  secret {
    name  = "snaptrade-consumer-key"
    value = var.snaptrade_consumer_key
  }

  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = "stock-service"
      image  = "${azurerm_container_registry.main.login_server}/${local.image_name}"
      cpu    = 1.0
      memory = "2Gi"

      env {
        name        = "ALPACA_API_KEY"
        secret_name = "alpaca-api-key"
      }
      env {
        name        = "ALPACA_API_SECRET"
        secret_name = "alpaca-api-secret"
      }
      env {
        name        = "SUPABASE_URL"
        secret_name = "supabase-url"
      }
      env {
        name        = "SUPABASE_KEY"
        secret_name = "supabase-key"
      }
      # Public JWKS endpoint for RS256 token verification, derived from the
      # Supabase project URL. Lets auth.py use the secure RS256 path instead of
      # the legacy HS256 fallback.
      env {
        name  = "SUPABASE_JWKS_URL"
        value = "${trimsuffix(var.supabase_url, "/")}/auth/v1/.well-known/jwks.json"
      }
      env {
        name        = "GO_CARDLESS_SECRET_ID"
        secret_name = "gocardless-secret-id"
      }
      env {
        name        = "GO_CARDLESS_SECRET_KEY"
        secret_name = "gocardless-secret-key"
      }
      env {
        name        = "BANK_ENCRYPTION_KEY"
        secret_name = "bank-encryption-key"
      }
      env {
        name        = "SNAPTRADE_CLIENT_ID"
        secret_name = "snaptrade-client-id"
      }
      env {
        name        = "SNAPTRADE_CONSUMER_KEY"
        secret_name = "snaptrade-consumer-key"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8001

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
