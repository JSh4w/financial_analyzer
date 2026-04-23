variable "resource_group_name" {
  description = "Azure Resource Group name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "acr_name" {
  description = "Azure Container Registry name (must be globally unique, lowercase, no spaces)"
  type        = string
}

variable "alpaca_api_key" {
  description = "Alpaca API key"
  type        = string
  sensitive   = true
}

variable "alpaca_api_secret" {
  description = "Alpaca API secret"
  type        = string
  sensitive   = true
}

variable "supabase_url" {
  description = "Supabase project URL"
  type        = string
  sensitive   = true
}

variable "supabase_key" {
  description = "Supabase service key"
  type        = string
  sensitive   = true
}

variable "supabase_anon_key" {
  description = "Supabase anon key"
  type        = string
  sensitive   = true
}

variable "gocardless_secret_id" {
  description = "GoCardless secret ID"
  type        = string
  sensitive   = true
}

variable "gocardless_secret_key" {
  description = "GoCardless secret key"
  type        = string
  sensitive   = true
}

variable "min_replicas" {
  description = "Minimum container replicas (set to 0 to scale to zero when idle)"
  type        = number
  default     = 0
}

variable "max_replicas" {
  description = "Maximum container replicas"
  type        = number
  default     = 1
}
