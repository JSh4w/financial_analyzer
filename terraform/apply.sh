#!/usr/bin/env bash
# Terraform deploy wrapper for the stock-service backend.
#
# Reproduces the safety/workflow of update-backend.sh on top of Terraform:
#   1. runs the test suite (via Dockerfile.test — same as CI) and gates on it
#   2. loads secrets from the backend .env into TF_VAR_* (via load-secrets.sh)
#   3. terraform init  -> plan -> apply
#   4. prints the backend URL
#
# Provisioning (RG, ACR, Container Apps env, container app, secrets) and the
# image build+push are all handled declaratively by the .tf files — this script
# is only the workflow glue Terraform shouldn't own.
#
# Usage:
#   ./apply.sh                      # test, plan, then apply (asks to confirm)
#   ./apply.sh -y                   # non-interactive (CI): fail hard, auto-approve
#   ./apply.sh --skip-tests         # skip the test gate
#   ./apply.sh --plan-only          # test + plan, no apply
#   ./apply.sh --env-file /path/.env
#
# Non-secret config (resource group, location, ACR name) comes from
# terraform.tfvars. Secrets come from the backend .env — never committed.

set -euo pipefail

# --- resolve script location so the script works from any CWD ------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_DIR="$SCRIPT_DIR/../backend/stock-service"

# --- defaults / flags ----------------------------------------------------------
SKIP_TESTS=0
AUTO_APPROVE=0
PLAN_ONLY=0
ENV_FILE=""

# Colours (disabled when not a TTY).
if [ -t 1 ]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; NC=''
fi
info()  { echo -e "${GREEN}$*${NC}"; }
warn()  { echo -e "${YELLOW}$*${NC}"; }
err()   { echo -e "${RED}$*${NC}" >&2; }

usage() {
  # Print the leading comment block (skip the shebang, stop at the first
  # non-comment line) with the leading "# " stripped.
  awk 'NR==1{next} /^#/{sub(/^# ?/,""); print; next} {exit}' "$0"
  exit "${1:-0}"
}

while [ $# -gt 0 ]; do
  case "$1" in
    --skip-tests)   SKIP_TESTS=1 ;;
    -y|--auto-approve) AUTO_APPROVE=1 ;;
    --plan-only)    PLAN_ONLY=1 ;;
    --env-file)     ENV_FILE="${2:-}"; shift ;;
    --env-file=*)   ENV_FILE="${1#*=}" ;;
    -h|--help)      usage 0 ;;
    *) err "Unknown argument: $1"; usage 1 ;;
  esac
  shift
done

# --- prerequisites -------------------------------------------------------------
command -v terraform &>/dev/null || { err "terraform not installed"; exit 1; }
command -v az &>/dev/null        || { err "Azure CLI not installed"; exit 1; }
az account show &>/dev/null      || { err "Not logged in to Azure. Run: az login"; exit 1; }

# --- 1. test gate (matches CI: build+run Dockerfile.test) ----------------------
if [ "$SKIP_TESTS" -eq 1 ]; then
  warn "Skipping tests (--skip-tests)."
else
  command -v docker &>/dev/null || { err "docker not installed (needed for the test gate; use --skip-tests to bypass)"; exit 1; }
  info "Running tests via Dockerfile.test ..."
  if ! ( docker build -f "$BACKEND_DIR/Dockerfile.test" -t stock-service:test "$BACKEND_DIR" \
         && docker run --rm stock-service:test ); then
    err "Tests failed."
    # Interactive sessions may override (parity with update-backend.sh); CI/-y fails hard.
    if [ "$AUTO_APPROVE" -eq 1 ] || [ ! -t 0 ]; then
      exit 1
    fi
    read -r -p "Continue with deploy anyway? (y/N): " CONTINUE
    [ "$CONTINUE" = "y" ] || exit 1
  else
    info "Tests passed."
  fi
fi

# --- 2. load secrets into TF_VAR_* --------------------------------------------
info "Loading secrets from backend .env ..."
# load-secrets.sh must be *sourced* so its exports reach terraform (a child process).
# shellcheck source=./load-secrets.sh
if [ -n "$ENV_FILE" ]; then
  source "$SCRIPT_DIR/load-secrets.sh" "$ENV_FILE"
else
  source "$SCRIPT_DIR/load-secrets.sh"
fi

# --- 3. init -------------------------------------------------------------------
info "terraform init ..."
terraform init -input=false

# --- 4. plan -------------------------------------------------------------------
info "terraform plan ..."
terraform plan -input=false -out=tfplan

if [ "$PLAN_ONLY" -eq 1 ]; then
  info "Plan-only mode; not applying. Review the plan above."
  exit 0
fi

# --- 5. apply ------------------------------------------------------------------
if [ "$AUTO_APPROVE" -eq 1 ]; then
  terraform apply -input=false tfplan
else
  read -r -p "Apply this plan? (y/N): " CONFIRM
  [ "$CONFIRM" = "y" ] || { warn "Aborted; no changes applied."; rm -f tfplan; exit 0; }
  terraform apply -input=false tfplan
fi
rm -f tfplan

# --- 6. report -----------------------------------------------------------------
BACKEND_URL="$(terraform output -raw backend_url 2>/dev/null || true)"
info "Deployment complete!"
[ -n "$BACKEND_URL" ] && echo "Backend URL: $BACKEND_URL"
