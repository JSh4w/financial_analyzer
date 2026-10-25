#!/usr/bin/env bash
# Load backend secrets from .env into TF_VAR_* environment variables so that
# Terraform uses the .env as the single source of truth — no secret values are
# duplicated into terraform.tfvars or committed to git.
#
# IMPORTANT: this script must be SOURCED, not executed, so the exports persist
# in your current shell:
#
#     cd terraform
#     source ./load-secrets.sh          # uses ../backend/stock-service/.env
#     source ./load-secrets.sh /path/to/.env   # or a custom .env path
#     terraform plan
#
# Terraform automatically reads any variable named TF_VAR_<var>, so these map
# onto the variables declared in variables.tf.

ENV_FILE="${1:-../backend/stock-service/.env}"

if [ ! -f "$ENV_FILE" ]; then
  echo "load-secrets: .env not found at '$ENV_FILE'" >&2
  # 'return' works when sourced; fall back to 'exit' if run directly.
  return 1 2>/dev/null || exit 1
fi

# Auto-export every assignment in the .env, then map the ones Terraform needs.
set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

export TF_VAR_alpaca_api_key="${ALPACA_API_KEY:-}"
export TF_VAR_alpaca_api_secret="${ALPACA_API_SECRET:-}"
export TF_VAR_supabase_url="${SUPABASE_URL:-}"
export TF_VAR_supabase_key="${SUPABASE_KEY:-}"
export TF_VAR_gocardless_secret_id="${GO_CARDLESS_SECRET_ID:-}"
export TF_VAR_gocardless_secret_key="${GO_CARDLESS_SECRET_KEY:-}"
export TF_VAR_bank_encryption_key="${BANK_ENCRYPTION_KEY:-}"

# Warn about anything Terraform requires but the .env didn't provide.
missing=()
[ -z "${ALPACA_API_KEY:-}" ]        && missing+=("ALPACA_API_KEY")
[ -z "${ALPACA_API_SECRET:-}" ]     && missing+=("ALPACA_API_SECRET")
[ -z "${SUPABASE_URL:-}" ]          && missing+=("SUPABASE_URL")
[ -z "${SUPABASE_KEY:-}" ]          && missing+=("SUPABASE_KEY")
[ -z "${GO_CARDLESS_SECRET_ID:-}" ] && missing+=("GO_CARDLESS_SECRET_ID")
[ -z "${GO_CARDLESS_SECRET_KEY:-}" ]&& missing+=("GO_CARDLESS_SECRET_KEY")
[ -z "${BANK_ENCRYPTION_KEY:-}" ]   && missing+=("BANK_ENCRYPTION_KEY")

if [ ${#missing[@]} -gt 0 ]; then
  echo "load-secrets: WARNING — these expected keys are empty/missing in $ENV_FILE:" >&2
  printf '  - %s\n' "${missing[@]}" >&2
fi

echo "load-secrets: exported TF_VAR_* from $ENV_FILE"
