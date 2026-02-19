#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="${1:-departure-board}"
REGION="${AWS_REGION:-eu-north-1}"
S3_DEPLOY_BUCKET="${SAM_BUCKET:-}" # set SAM_BUCKET or pass --s3-bucket to sam deploy

echo "==> Building SAM application..."
sam build

echo "==> Deploying stack: $STACK_NAME to $REGION..."
sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --no-confirm-changeset

# Get outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

FRONTEND_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucket`].OutputValue' \
  --output text)

FRONTEND_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendUrl`].OutputValue' \
  --output text)

# Inject the API URL into the frontend and upload to S3
echo "==> Uploading frontend to s3://$FRONTEND_BUCKET ..."
TMPDIR=$(mktemp -d)
sed "s|window.APP_CONFIG?.apiBase || ''|'${API_URL}'|" frontend/index.html > "$TMPDIR/index.html"
aws s3 cp "$TMPDIR/index.html" "s3://$FRONTEND_BUCKET/index.html" --content-type "text/html"
rm -rf "$TMPDIR"

echo ""
echo "===================================="
echo "  Deployment complete!"
echo "  API:      $API_URL"
echo "  Frontend: $FRONTEND_URL"
echo "===================================="
