# =====================================================
# SAVEYOURDOCUMENT - Quick Deploy Script for Cloud Run
# By Mitrixo Systems
# =====================================================
#
# Prerequisites:
#   - Google Cloud SDK installed (gcloud)
#   - Authenticated: gcloud auth login
#   - Project set: gcloud config set project YOUR_PROJECT_ID
#
# Usage:
#   .\deploy-cloudrun.ps1 -ProjectId "your-gcp-project-id" -GeminiApiKey "your-gemini-key"

param(
    [Parameter(Mandatory=$true)]
    [string]$ProjectId,
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-central1",
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "saveyourdocument",
    
    [Parameter(Mandatory=$false)]
    [string]$GeminiApiKey = ""
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  SAVEYOURDOCUMENT - Cloud Run Deployment"     -ForegroundColor Cyan
Write-Host "  Powered by Mitrixo Systems"                  -ForegroundColor DarkGray
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Set project
Write-Host "[1/6] Setting GCP project to: $ProjectId" -ForegroundColor Yellow
gcloud config set project $ProjectId

# Step 2: Enable required APIs
Write-Host "[2/6] Enabling required APIs..." -ForegroundColor Yellow
gcloud services enable cloudbuild.googleapis.com run.googleapis.com artifactregistry.googleapis.com containerregistry.googleapis.com

# Step 3: Create Artifact Registry (ignore error if exists)
Write-Host "[3/6] Creating Artifact Registry repository..." -ForegroundColor Yellow
try {
    gcloud artifacts repositories create $ServiceName --repository-format=docker --location=$Region --description="SAVEYOURDOCUMENT Docker images" 2>$null
    Write-Host "  Repository created." -ForegroundColor Green
} catch {
    Write-Host "  Repository already exists, continuing..." -ForegroundColor DarkGray
}

# Step 4: Build and push using Cloud Build
Write-Host "[4/6] Building Docker image via Cloud Build..." -ForegroundColor Yellow
$commitSha = "manual"
try {
    $commitSha = (git rev-parse --short HEAD 2>$null).Trim()
    if (-not $commitSha) { $commitSha = "manual" }
} catch {
    $commitSha = "manual"
}
Write-Host "  Using Commit SHA: $commitSha" -ForegroundColor DarkGray
gcloud builds submit --config=cloudbuild.yaml --substitutions="_REGION=$Region,_SERVICE_NAME=$ServiceName,_REPO=$ServiceName,_COMMIT_SHA=$commitSha" .

# Step 5: Set Gemini API key if provided
if ($GeminiApiKey) {
    Write-Host "[5/6] Setting GEMINI_API_KEY environment variable..." -ForegroundColor Yellow
    gcloud run services update $ServiceName --region=$Region --set-env-vars="GEMINI_API_KEY=$GeminiApiKey"
} else {
    Write-Host "[5/6] No GEMINI_API_KEY provided. Users will need to enter it in the UI." -ForegroundColor DarkYellow
    Write-Host "  To set it later: gcloud run services update $ServiceName --region=$Region --set-env-vars='GEMINI_API_KEY=your-key'" -ForegroundColor DarkGray
}

# Step 6: Get service URL
Write-Host "[6/6] Retrieving service URL..." -ForegroundColor Yellow
$serviceUrl = gcloud run services describe $ServiceName --region=$Region --format="value(status.url)"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Service URL: $serviceUrl" -ForegroundColor White
Write-Host "  Region:      $Region" -ForegroundColor DarkGray
Write-Host "  Project:     $ProjectId" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Open in browser: Start-Process '$serviceUrl'" -ForegroundColor Cyan
Write-Host ""
