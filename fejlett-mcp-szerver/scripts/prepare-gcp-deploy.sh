#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-europe-west1}"
ARTIFACT_REPO="${ARTIFACT_REPO:-fejlett-mcp-szerver}"
SERVICE_NAME="${SERVICE_NAME:-fejlett-mcp-szerver}"
RUNTIME_SA_NAME="${RUNTIME_SA_NAME:-${SERVICE_NAME}-run}"
DEPLOY_SA_NAME="${DEPLOY_SA_NAME:-${SERVICE_NAME}-deploy}"
GITHUB_MCP_SECRET="${GITHUB_MCP_SECRET:-${SERVICE_NAME}-github-pat}"
IMAGE_NAME="${IMAGE_NAME:-${SERVICE_NAME}}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M%S)}"
BUILD_PLATFORM="${BUILD_PLATFORM:-linux/amd64}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-}"
WIF_POOL="${WIF_POOL:-github}"
WIF_PROVIDER="${WIF_PROVIDER:-github}"
DEPLOY_MODE="prepare"

usage() {
  cat <<'EOF'
Használat:
  export PROJECT_ID="<Te GCP Projekted ID-ja>"
  ./scripts/prepare-gcp-deploy.sh
  ./scripts/prepare-gcp-deploy.sh --deploy

Leírás:
  API-k, Artifact Registry, két service account, GitHub OIDC
  (Workload Identity Federation) és a GitHub MCP token Secret Managerben.
  A projekt a PROJECT_ID változóból jön, a GitHub repo a git origin remote-ból,
  a token a GITHUB_PERSONAL_ACCESS_TOKEN környezeti változóból.
  Egyik sem kerül a repóba.

  A futásidejű fiók csak a saját secretet és a registry olvasását kapja.
  A deploy fiók csak image írást, Cloud Run deployt és a futásidejű fiók
  használatát kapja. A szkript nem ad szerepet a bejelentkezett felhasználónak.

Változók:
  PROJECT_ID                     GCP projekt azonosító (kötelező)
  REGION                         GCP régió (alap: europe-west1)
  ARTIFACT_REPO                  Artifact Registry repo (alap: fejlett-mcp-szerver)
  SERVICE_NAME                   Cloud Run service (alap: fejlett-mcp-szerver)
  RUNTIME_SA_NAME                Futásidejű fiók (alap: <SERVICE_NAME>-run)
  DEPLOY_SA_NAME                 CI deploy fiók (alap: <SERVICE_NAME>-deploy)
  GITHUB_MCP_SECRET              Secret neve, nem az értéke (alap: <SERVICE_NAME>-github-pat)
  GITHUB_PERSONAL_ACCESS_TOKEN   GitHub MCP token, csak a shellben
  GITHUB_REPOSITORY              owner/név. Üresen a git originból jön.
  WIF_POOL                       Workload Identity pool (alap: github)
  WIF_PROVIDER                   OIDC provider (alap: github)

Opciók:
  --deploy                       Build, push és Cloud Run deploy
  --help                         Súgó
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --deploy)
      DEPLOY_MODE="deploy"
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

APP_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$APP_PATH/.." && pwd)"

if [[ -z "$GITHUB_REPOSITORY" ]]; then
  remote="$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null || true)"
  GITHUB_REPOSITORY="$(printf '%s' "$remote" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')"
fi
if [[ "$GITHUB_REPOSITORY" != */* ]]; then
  echo "Hiba: GITHUB_REPOSITORY kötelező (owner/név), vagy legyen origin remote." >&2
  exit 1
fi

if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" && -f "$APP_PATH/.env" ]]; then
  GITHUB_PERSONAL_ACCESS_TOKEN="$(
    python3 - "$APP_PATH/.env" <<'PY'
import sys
from pathlib import Path
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if line.startswith("GITHUB_PERSONAL_ACCESS_TOKEN="):
        print(line.split("=", 1)[1].strip().strip("'\""), end="")
        break
PY
  )"
fi

if [[ ! -d "$APP_PATH" ]]; then
  echo "Az app könyvtára nem található: $APP_PATH" >&2
  exit 1
fi

if [[ ! -f "$APP_PATH/Dockerfile" ]]; then
  echo "A Dockerfile hiányzik itt: $APP_PATH" >&2
  exit 1
fi

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Hiányzó parancs: $1" >&2
    exit 1
  fi
}

require_cmd gcloud
require_cmd docker

ensure_sa() {
  local name="$1"
  local display="$2"
  local email="${name}@${PROJECT_ID}.iam.gserviceaccount.com"
  if ! gcloud iam service-accounts describe "$email" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$name" \
      --project="$PROJECT_ID" \
      --display-name="$display" >/dev/null
  fi
  printf '%s' "$email"
}

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "[1/6] GCP projekt beállítása"
gcloud config set project "$PROJECT_ID" >/dev/null

echo "[2/6] API-k"
if ! gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com \
  --project="$PROJECT_ID" 2>&1; then
  echo "HIBA: a bejelentkezett fiók nem tud API-t bekapcsolni ezen a projekten." >&2
  echo "A gcloud CLI fiókja: $(gcloud config get-value account 2>/dev/null || echo 'nincs bejelentkezve')" >&2
  echo "Ez a szkript nem ad neki szerepet. Owner vagy a megfelelő admin szerepek kellenek előre." >&2
  exit 1
fi

echo "[3/6] Artifact Registry"
if ! gcloud artifacts repositories describe "$ARTIFACT_REPO" \
  --location="$REGION" \
  --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$ARTIFACT_REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --project="$PROJECT_ID" \
    --description="Docker images for MCP services" >/dev/null
fi
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "[4/6] Service accountok"
RUNTIME_SA="$(ensure_sa "$RUNTIME_SA_NAME" "Cloud Run runtime")"
DEPLOY_SA="$(ensure_sa "$DEPLOY_SA_NAME" "GitHub Actions deploy")"

# A korábbi, túl széles projekt-szerepek levétele a futásidejű és a régi fiókról.
LEGACY_SA="${SERVICE_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com"
for legacy in "$RUNTIME_SA" "$DEPLOY_SA" "$LEGACY_SA"; do
  for role in \
    roles/run.admin \
    roles/artifactregistry.reader \
    roles/artifactregistry.writer \
    roles/iam.serviceAccountUser; do
    gcloud projects remove-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:${legacy}" \
      --role="$role" >/dev/null 2>&1 || true
  done
done
if [[ "$LEGACY_SA" != "$RUNTIME_SA" && "$LEGACY_SA" != "$DEPLOY_SA" ]]; then
  if gcloud iam service-accounts describe "$LEGACY_SA" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud iam service-accounts delete "$LEGACY_SA" --project="$PROJECT_ID" --quiet
  fi
fi

gcloud artifacts repositories add-iam-policy-binding "$ARTIFACT_REPO" \
  --location="$REGION" \
  --project="$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/artifactregistry.reader" >/dev/null

gcloud artifacts repositories add-iam-policy-binding "$ARTIFACT_REPO" \
  --location="$REGION" \
  --project="$PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA}" \
  --role="roles/artifactregistry.writer" >/dev/null

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA}" \
  --role="roles/run.developer" >/dev/null

gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --project="$PROJECT_ID" \
  --role="roles/iam.serviceAccountUser" \
  --member="serviceAccount:${DEPLOY_SA}" >/dev/null

echo "[5/6] GitHub OIDC"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
WIF_PROVIDER_RESOURCE="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL}/providers/${WIF_PROVIDER}"
WIF_MEMBER="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${WIF_POOL}/attribute.repository/${GITHUB_REPOSITORY}"
ATTR_CONDITION="assertion.repository=='${GITHUB_REPOSITORY}' && assertion.ref=='refs/heads/main'"

pool_state="$(
  gcloud iam workload-identity-pools describe "$WIF_POOL" \
    --location=global \
    --project="$PROJECT_ID" \
    --format='value(state)' 2>/dev/null || true
)"
if [[ -z "$pool_state" ]]; then
  gcloud iam workload-identity-pools create "$WIF_POOL" \
    --location=global \
    --project="$PROJECT_ID" \
    --display-name="GitHub Actions" >/dev/null
elif [[ "$pool_state" == "DELETED" ]]; then
  gcloud iam workload-identity-pools undelete "$WIF_POOL" \
    --location=global \
    --project="$PROJECT_ID" >/dev/null
fi

provider_state="$(
  gcloud iam workload-identity-pools providers describe "$WIF_PROVIDER" \
    --workload-identity-pool="$WIF_POOL" \
    --location=global \
    --project="$PROJECT_ID" \
    --format='value(state)' 2>/dev/null || true
)"
if [[ "$provider_state" == "DELETED" ]]; then
  gcloud iam workload-identity-pools providers undelete "$WIF_PROVIDER" \
    --workload-identity-pool="$WIF_POOL" \
    --location=global \
    --project="$PROJECT_ID" >/dev/null
  provider_state="ACTIVE"
fi
if [[ -z "$provider_state" ]]; then
  created=0
  for _ in 1 2 3 4 5 6; do
    if gcloud iam workload-identity-pools providers create-oidc "$WIF_PROVIDER" \
      --workload-identity-pool="$WIF_POOL" \
      --location=global \
      --project="$PROJECT_ID" \
      --display-name="GitHub" \
      --issuer-uri="https://token.actions.githubusercontent.com" \
      --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
      --attribute-condition="$ATTR_CONDITION" >/dev/null; then
      created=1
      break
    fi
    sleep 3
  done
  if [[ "$created" -ne 1 ]]; then
    echo "A Workload Identity provider nem jött létre." >&2
    exit 1
  fi
else
  gcloud iam workload-identity-pools providers update-oidc "$WIF_PROVIDER" \
    --workload-identity-pool="$WIF_POOL" \
    --location=global \
    --project="$PROJECT_ID" \
    --attribute-condition="$ATTR_CONDITION" >/dev/null
fi

gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" \
  --project="$PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="$WIF_MEMBER" >/dev/null

echo "[6/6] GitHub MCP token a Secret Managerben"
if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
  if ! gcloud secrets describe "$GITHUB_MCP_SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
    printf '%s' "$GITHUB_PERSONAL_ACCESS_TOKEN" | gcloud secrets create "$GITHUB_MCP_SECRET" \
      --project="$PROJECT_ID" \
      --replication-policy="automatic" \
      --data-file=- >/dev/null
  else
    printf '%s' "$GITHUB_PERSONAL_ACCESS_TOKEN" | gcloud secrets versions add "$GITHUB_MCP_SECRET" \
      --project="$PROJECT_ID" \
      --data-file=- >/dev/null
  fi
  gcloud secrets add-iam-policy-binding "$GITHUB_MCP_SECRET" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
  echo "Secret frissítve. A token értéke nem került fájlba és nem jelenik meg a kimeneten."
else
  echo "GITHUB_PERSONAL_ACCESS_TOKEN nincs megadva. A Cloud Run GitHub MCP tooljai így nem indulnak." >&2
fi
unset GITHUB_PERSONAL_ACCESS_TOKEN

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  gh variable set GCP_PROJECT_ID --repo "$GITHUB_REPOSITORY" --body "$PROJECT_ID" >/dev/null
  gh variable set GCP_REGION --repo "$GITHUB_REPOSITORY" --body "$REGION" >/dev/null
  gh variable set GCP_SERVICE_NAME --repo "$GITHUB_REPOSITORY" --body "$SERVICE_NAME" >/dev/null
  gh variable set GCP_ARTIFACT_REPO --repo "$GITHUB_REPOSITORY" --body "$ARTIFACT_REPO" >/dev/null
  gh variable set GCP_IMAGE_NAME --repo "$GITHUB_REPOSITORY" --body "$IMAGE_NAME" >/dev/null
  gh variable set GCP_WIF_PROVIDER --repo "$GITHUB_REPOSITORY" --body "$WIF_PROVIDER_RESOURCE" >/dev/null
  gh variable set GCP_DEPLOY_SERVICE_ACCOUNT --repo "$GITHUB_REPOSITORY" --body "$DEPLOY_SA" >/dev/null
  gh variable set GCP_RUNTIME_SERVICE_ACCOUNT --repo "$GITHUB_REPOSITORY" --body "$RUNTIME_SA" >/dev/null
  gh variable set GCP_GITHUB_MCP_SECRET --repo "$GITHUB_REPOSITORY" --body "$GITHUB_MCP_SECRET" >/dev/null
  echo "GitHub Actions változók beírva. Az értékek a GitHubon vannak, nem a workflow fájlban."
else
  echo "A gh CLI nincs belépve. A workflow ezeket a változókat várja a repón: GCP_PROJECT_ID, GCP_REGION, GCP_SERVICE_NAME, GCP_ARTIFACT_REPO, GCP_IMAGE_NAME, GCP_WIF_PROVIDER, GCP_DEPLOY_SERVICE_ACCOUNT, GCP_RUNTIME_SERVICE_ACCOUNT, GCP_GITHUB_MCP_SECRET." >&2
fi

umask 077
cat > "$APP_PATH/.env.gcp" <<EOF
PROJECT_ID=${PROJECT_ID}
REGION=${REGION}
ARTIFACT_REPO=${ARTIFACT_REPO}
SERVICE_NAME=${SERVICE_NAME}
RUNTIME_SA=${RUNTIME_SA}
DEPLOY_SA=${DEPLOY_SA}
IMAGE_URI=${IMAGE_URI}
MCP_TRANSPORT=streamable-http
MCP_EXTERNALS=/app/externals.cloudrun.json
GITHUB_MCP_SECRET=${GITHUB_MCP_SECRET}
WIF_PROVIDER=${WIF_PROVIDER_RESOURCE}
EOF
chmod 600 "$APP_PATH/.env.gcp"

echo
echo "Kész. A helyi .env.gcp gitignore alatt van, ne commitold."
echo "Image: ${IMAGE_URI}"

if [[ "$DEPLOY_MODE" == "deploy" ]]; then
  echo "[deploy] Image build és push a host Docker hitelesítésével"
  docker build \
    --platform "$BUILD_PLATFORM" \
    -t "$IMAGE_URI" \
    "$APP_PATH"
  docker push "$IMAGE_URI"

  echo "[deploy] Cloud Run"
  SECRET_ARGS=()
  if gcloud secrets describe "$GITHUB_MCP_SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
    SECRET_ARGS=(--set-secrets="GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_MCP_SECRET}:latest")
  fi
  gcloud run deploy "$SERVICE_NAME" \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --image="$IMAGE_URI" \
    --allow-unauthenticated \
    --service-account="$RUNTIME_SA" \
    --set-env-vars="MCP_TRANSPORT=streamable-http,MCP_EXTERNALS=/app/externals.cloudrun.json" \
    "${SECRET_ARGS[@]}"
fi
