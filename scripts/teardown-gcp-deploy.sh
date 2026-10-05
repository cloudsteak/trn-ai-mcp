#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-fejlett-mcp-szerver}"
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-europe-west1}"
ARTIFACT_REPO="${ARTIFACT_REPO:-fejlett-mcp-szerver}"
SERVICE_NAME="${SERVICE_NAME:-fejlett-mcp-szerver}"
RUNTIME_SA_NAME="${RUNTIME_SA_NAME:-${SERVICE_NAME}-run}"
DEPLOY_SA_NAME="${DEPLOY_SA_NAME:-${SERVICE_NAME}-deploy}"
GITHUB_MCP_SECRET="${GITHUB_MCP_SECRET:-${SERVICE_NAME}-github-pat}"
WIF_POOL="${WIF_POOL:-github}"
WIF_PROVIDER="${WIF_PROVIDER:-github}"
DISABLE_APIS="${DISABLE_APIS:-true}"
FORCE="false"

usage() {
  cat <<'EOF'
Használat:
  export PROJECT_ID="$PROJECT_ID"
  ./scripts/teardown-gcp-deploy.sh --force
  ./scripts/teardown-gcp-deploy.sh --yes

Leírás:
  Törli a Cloud Run service-t, az Artifact Registry repót, a futásidejű és a
  deploy service accountot, a Secret Manager secretet és a Workload Identity
  poolt. A projekt azonosító a PROJECT_ID változó. A szkript nem ír ki és nem
  tárol tokent.

Változók:
  PROJECT_ID           GCP projekt azonosító (kötelező)
  APP_DIR              App könyvtára (alap: fejlett-mcp-szerver)
  REGION               GCP régió (alap: europe-west1)
  ARTIFACT_REPO        Artifact Registry repo (alap: fejlett-mcp-szerver)
  SERVICE_NAME         Cloud Run service (alap: fejlett-mcp-szerver)
  RUNTIME_SA_NAME      Futásidejű fiók (alap: <SERVICE_NAME>-run)
  DEPLOY_SA_NAME       Deploy fiók (alap: <SERVICE_NAME>-deploy)
  GITHUB_MCP_SECRET    Secret neve (alap: <SERVICE_NAME>-github-pat)
  DISABLE_APIS         API-k kikapcsolása (alap: true)

Opciók:
  --force, --yes   Nincs interaktív megerősítés
  --keep-apis      Ne kapcsolja ki az API-kat
  --help           Súgó
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force|--yes)
      FORCE="true"
      shift
      ;;
    --keep-apis)
      DISABLE_APIS="false"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Ismeretlen argumentum: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$PROJECT_ID" ]]; then
  echo "A PROJECT_ID környezeti változó kötelező." >&2
  usage >&2
  exit 1
fi

if [[ "$FORCE" != "true" ]]; then
  echo "VIGYÁZAT: ez TÖRLI a következőket a(z) $PROJECT_ID projektben:"
  echo "  - Cloud Run service: $SERVICE_NAME"
  echo "  - Artifact Registry repo: $ARTIFACT_REPO"
  echo "  - Service accountok: ${RUNTIME_SA_NAME}, ${DEPLOY_SA_NAME}, ${SERVICE_NAME}-sa"
  echo "  - Secret: ${GITHUB_MCP_SECRET}"
  echo "  - Workload Identity pool: ${WIF_POOL}"
  if [[ "$DISABLE_APIS" == "true" ]]; then
    echo "  - API-k: Cloud Run, Artifact Registry, Secret Manager, IAM, IAM Credentials"
  fi
  echo ""
  read -r -p "Írd be a DELETE szót a folytatáshoz: " confirm
  if [[ "$confirm" != "DELETE" ]]; then
    echo "Megszakítva."
    exit 1
  fi
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_PATH="${REPO_ROOT}/${APP_DIR}"

if [[ -f "$APP_PATH/.env.gcp" ]]; then
  rm -f "$APP_PATH/.env.gcp"
  echo "Törölve: $APP_PATH/.env.gcp"
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Hiányzó parancs: $1" >&2
    exit 1
  fi
}

require_cmd gcloud

ACTIVE_ACCOUNT="$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null || true)"

# Cloud Run service delete
if gcloud run services describe "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" >/dev/null 2>&1; then
  echo "[1/6] Cloud Run service törlése: $SERVICE_NAME"
  gcloud run services delete "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --quiet
else
  echo "[1/6] Cloud Run service nem létezik: $SERVICE_NAME"
fi

# Artifact Registry repo delete
if gcloud artifacts repositories describe "$ARTIFACT_REPO" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "[2/6] Artifact Registry repo törlése: $ARTIFACT_REPO"
  gcloud artifacts repositories delete "$ARTIFACT_REPO" \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --quiet
else
  echo "[2/6] Artifact Registry repo nem létezik: $ARTIFACT_REPO"
fi

if [[ -n "$ACTIVE_ACCOUNT" ]] && gcloud projects get-iam-policy "$PROJECT_ID" \
  --flatten="bindings[].members" \
  --filter="bindings.members:user:${ACTIVE_ACCOUNT} AND (bindings.role=roles/owner OR bindings.role=roles/editor)" \
  --format="value(bindings.role)" 2>/dev/null | grep -q .; then
  echo "[3/6] A Prepare által adott felhasználói szerepek levétele"
  for role in \
    roles/run.admin \
    roles/artifactregistry.reader \
    roles/artifactregistry.writer \
    roles/iam.serviceAccountUser; do
    gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
      --member="user:${ACTIVE_ACCOUNT}" \
      --role="$role" \
      >/dev/null 2>&1 || true
  done
fi

if gcloud secrets describe "$GITHUB_MCP_SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "[4/6] Secret törlése: $GITHUB_MCP_SECRET"
  gcloud secrets delete "$GITHUB_MCP_SECRET" --project="$PROJECT_ID" --quiet
else
  echo "[4/6] Secret nem létezik: $GITHUB_MCP_SECRET"
fi

echo "[5/6] Service accountok törlése"
for name in "$RUNTIME_SA_NAME" "$DEPLOY_SA_NAME" "${SERVICE_NAME}-sa"; do
  email="${name}@${PROJECT_ID}.iam.gserviceaccount.com"
  if gcloud iam service-accounts describe "$email" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud iam service-accounts delete "$email" --project="$PROJECT_ID" --quiet
  fi
done

if gcloud iam workload-identity-pools describe "$WIF_POOL" \
  --location=global \
  --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "[wif] Workload Identity pool törlése: $WIF_POOL"
  gcloud iam workload-identity-pools providers delete "$WIF_PROVIDER" \
    --workload-identity-pool="$WIF_POOL" \
    --location=global \
    --project="$PROJECT_ID" \
    --quiet >/dev/null 2>&1 || true
  gcloud iam workload-identity-pools delete "$WIF_POOL" \
    --location=global \
    --project="$PROJECT_ID" \
    --quiet >/dev/null 2>&1 || true
else
  echo "[wif] Workload Identity pool nem létezik: $WIF_POOL"
fi

if [[ "$DISABLE_APIS" == "true" ]]; then
  echo "[6/6] API-k kikapcsolása"
  for api in \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    cloudbuild.googleapis.com \
    iamcredentials.googleapis.com \
    iam.googleapis.com; do
    gcloud services disable "$api" --project="$PROJECT_ID" --force >/dev/null 2>&1 || true
  done
else
  echo "[6/6] API-k megtartva (--keep-apis)"
fi

remote="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
GITHUB_REPOSITORY="$(printf '%s' "$remote" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')"
if [[ "$GITHUB_REPOSITORY" == */* ]] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  for name in \
    GCP_PROJECT_ID \
    GCP_REGION \
    GCP_SERVICE_NAME \
    GCP_ARTIFACT_REPO \
    GCP_IMAGE_NAME \
    GCP_WIF_PROVIDER \
    GCP_DEPLOY_SERVICE_ACCOUNT \
    GCP_RUNTIME_SERVICE_ACCOUNT \
    GCP_GITHUB_MCP_SECRET; do
    gh variable delete "$name" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1 || true
  done
fi

echo
echo "A GCP előkészítés törölve. A helyi .env.gcp is törölve lett."
