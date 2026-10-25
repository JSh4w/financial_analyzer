resource "azurerm_container_registry" "main" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true
}

# Content hash of the backend source. When any tracked source file changes,
# output_sha changes, which changes the image tag below and triggers a rebuild
# + a new Container App revision — mirroring what update-backend.sh does.
data "archive_file" "stock_service_src" {
  type        = "zip"
  source_dir  = "${path.root}/../backend/stock-service"
  output_path = "${path.root}/.terraform/tmp/stock-service-src.zip"

  # Mirror .dockerignore: exclude what never ends up in the image so unrelated
  # churn (caches, local data, tests) doesn't force needless rebuilds.
  excludes = [
    "__pycache__",
    ".pytest_cache",
    "data",
    "tests",
    "docs",
    "app/cpp/hmm/build",
  ]
}

locals {
  # Short, deterministic tag derived from source content.
  image_tag  = substr(data.archive_file.stock_service_src.output_sha, 0, 12)
  image_name = "stock-service:${local.image_tag}"
}

# Build and push the backend image whenever the source content changes.
# Tags both the content-hash tag (drives new revisions) and :latest (parity
# with the shell scripts).
resource "null_resource" "build_stock_service" {
  depends_on = [azurerm_container_registry.main]

  triggers = {
    source_sha = data.archive_file.stock_service_src.output_sha
  }

  provisioner "local-exec" {
    command = <<-EOT
      az acr build \
        --registry ${azurerm_container_registry.main.name} \
        --image ${local.image_name} \
        --image stock-service:latest \
        --file ${path.root}/../backend/stock-service/Dockerfile \
        ${path.root}/../backend/stock-service
    EOT
  }
}
