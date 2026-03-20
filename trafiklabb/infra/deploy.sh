#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Stockholm Departure Board - CDK Deploy ==="

# Step 1: Build Lambda layer for gtfs-realtime-bindings
echo ">> Building Lambda layer..."
LAYER_DIR="$SCRIPT_DIR/../backend/layer/python"
mkdir -p "$LAYER_DIR"
pip install gtfs-realtime-bindings -t "$LAYER_DIR" --quiet

# Step 2: Bootstrap CDK (only needed once per account/region)
echo ">> Bootstrapping CDK (if needed)..."
npx cdk bootstrap 2>/dev/null || true

# Step 2: Deploy the stack
echo ">> Deploying CDK stack..."
npx cdk deploy --require-approval never --outputs-file cdk-outputs.json

# Step 3: Extract outputs
API_URL=$(node -e "const o=require('./cdk-outputs.json'); console.log(o.DepartureBoardStack.ApiUrl)")
CLOUDFRONT_URL=$(node -e "const o=require('./cdk-outputs.json'); console.log(o.DepartureBoardStack.CloudFrontUrl)")
BUCKET_NAME=$(node -e "const o=require('./cdk-outputs.json'); console.log(o.DepartureBoardStack.BucketName)")

echo ""
echo ">> Injecting API URL into frontend..."

# Step 4: Inject API_BASE config into index.html and re-upload
FRONTEND_DIR="$SCRIPT_DIR/../frontend"
TEMP_DIR=$(mktemp -d)

# Inject the APP_CONFIG before the closing </head> tag (portable across macOS and Linux)
sed "s|</head>|<script>window.APP_CONFIG = { apiBase: '${API_URL%/}' };</script></head>|" "$FRONTEND_DIR/index.html" > "$TEMP_DIR/index.html"
sed "s|</head>|<script>window.APP_CONFIG = { apiBase: '${API_URL%/}' };</script></head>|" "$FRONTEND_DIR/map.html" > "$TEMP_DIR/map.html"

# Upload the modified frontend to S3
aws s3 cp "$TEMP_DIR/index.html" "s3://$BUCKET_NAME/index.html" --content-type "text/html"
aws s3 cp "$TEMP_DIR/map.html" "s3://$BUCKET_NAME/map.html" --content-type "text/html"

# Invalidate CloudFront cache
DIST_ID=$(aws cloudformation describe-stacks --stack-name DepartureBoardStack \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontUrl'].OutputValue" --output text | \
  sed 's|https://||' | sed 's|\.cloudfront\.net||')

if [ -n "$DIST_ID" ]; then
  echo ">> Invalidating CloudFront cache..."
  # Get the actual distribution ID from the domain name
  REAL_DIST_ID=$(aws cloudfront list-distributions \
    --query "DistributionList.Items[?DomainName=='${DIST_ID}.cloudfront.net'].Id" --output text)
  if [ -n "$REAL_DIST_ID" ]; then
    aws cloudfront create-invalidation --distribution-id "$REAL_DIST_ID" --paths "/*" >/dev/null
  fi
fi

# Clean up
rm -rf "$TEMP_DIR"

echo ""
echo "=== Deployment Complete ==="
echo "  API:      $API_URL"
echo "  Website:  $CLOUDFRONT_URL"
echo ""
echo "Open $CLOUDFRONT_URL in your browser!"
