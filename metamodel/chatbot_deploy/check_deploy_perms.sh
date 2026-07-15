#!/usr/bin/env bash
# Read-only probe: checks whether the current AWS profile can deploy a container
# to App Runner. Creates/changes NOTHING — every call is a describe/list/dry-run.
#
# Usage:  AWS_PROFILE=alexa bash check_deploy_perms.sh
set -u

PROFILE="${AWS_PROFILE:-alexa}"
REGION="$(aws configure get region --profile "$PROFILE" 2>/dev/null || echo us-west-2)"
echo "Profile: $PROFILE   Region: $REGION"
echo "======================================================"

check () {
  local label="$1"; shift
  # Run the (read-only) call; report OK / DENIED / other error.
  if out="$("$@" 2>&1)"; then
    echo "  ✅  $label"
  else
    if echo "$out" | grep -qiE 'AccessDenied|not authorized|UnauthorizedOperation'; then
      echo "  ❌  $label  — ACCESS DENIED (role lacks this permission)"
    else
      echo "  ⚠️  $label  — other error: $(echo "$out" | head -1)"
    fi
  fi
}

echo "Who am I?"
aws sts get-caller-identity --profile "$PROFILE" --output text 2>&1 | sed 's/^/  /'
echo

echo "ECR (store the Docker image):"
check "ecr: get login token"      aws ecr get-authorization-token   --profile "$PROFILE" --region "$REGION"
check "ecr: list repositories"    aws ecr describe-repositories     --profile "$PROFILE" --region "$REGION"
echo

echo "App Runner (run the container):"
check "apprunner: list services"  aws apprunner list-services       --profile "$PROFILE" --region "$REGION"
echo

echo "IAM (the usual blocker — App Runner needs a PassRole):"
check "iam: list roles"           aws iam list-roles                --profile "$PROFILE" --max-items 1
echo

echo "======================================================"
echo "Reading: all ✅ = you can likely deploy yourself."
echo "Any ❌ (especially ECR or App Runner) = ask whoever manages"
echo "this AWS account to grant those permissions to the role,"
echo "or to deploy on your behalf."
