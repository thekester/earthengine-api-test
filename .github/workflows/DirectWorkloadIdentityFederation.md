# Authenticate to Google Cloud from GitHub Actions with Direct Workload Identity Federation

## Prerequisites

- The [gcloud](https://cloud.google.com/sdk/docs/install) command-line tool must be installed.
- A Google Cloud project is required, with the appropriate permissions to create resources.

## Creating a Google Cloud Project ID

To create a new Google Cloud project and obtain a `PROJECT_ID`, use the following command:

```bash
# Replace "PROJECT_NAME" with your desired project name.

gcloud projects create PROJECT_NAME
```

After creating the project, set the project ID as the active project:

```bash
# Replace "PROJECT_ID" with your actual project ID.

gcloud config set project PROJECT_ID
```

You can list all your projects to verify the `PROJECT_ID`:

```bash
gcloud projects list
```

## Obtaining GitHub Organization (`GITHUB_ORG`)

To obtain the `GITHUB_ORG` value, you need the name of your GitHub organization. This can be found by visiting the GitHub website and navigating to your organization. The `GITHUB_ORG` is the part of the URL after `https://github.com/` and before the repository name. For example, if your repository URL is:

```
https://github.com/my-org/my-repo
```

Then `GITHUB_ORG` would be `my-org`.

Alternatively, if you are using a personal repository, the `GITHUB_ORG` value would be your GitHub username.

### Example for Your Case

In your case, the repository URL is:

```
https://github.com/username/earthengine-api-test
```

Here, `username` is your GitHub username, so your `GITHUB_ORG` value would be `username`.

## Step-by-Step Guide

### Step 1: Create a Workload Identity Pool
Create a Workload Identity Pool to enable GitHub Actions to authenticate to Google Cloud.

```bash
# TODO: replace ${PROJECT_ID} with your value below.

gcloud iam workload-identity-pools create "github" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions Pool"
```

### Step 2: Get the Full ID of the Workload Identity Pool

The full ID of the Workload Identity Pool is required for future commands.

```bash
# TODO: replace ${PROJECT_ID} with your value below.

gcloud iam workload-identity-pools describe "github" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --format="value(name)"
```

The value should be of the format:
```
projects/123456789/locations/global/workloadIdentityPools/github
```

### Step 3: Create a Workload Identity Provider

This step creates a Workload Identity Provider in the pool you just created. **Note:** It is important to add an attribute condition to restrict admission to trusted GitHub organizations.

```bash
# TODO: replace ${PROJECT_ID} and ${GITHUB_ORG} with your values below.

gcloud iam workload-identity-pools providers create-oidc "my-repo" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github" \
  --display-name="My GitHub repo Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

**Important**: Make sure to map incoming claims to attributes for assertion conditions and IAM policy.

### Step 4: Extract the Workload Identity Provider Resource Name

Extract the Workload Identity Provider resource name to use it in GitHub Actions.

```bash
# TODO: replace ${PROJECT_ID} with your value below.

gcloud iam workload-identity-pools providers describe "my-repo" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github" \
  --format="value(name)"
```

### Step 5: Create a Service Account
If you do not have a service account, you need to create one to allow GitHub Actions to authenticate to Google Cloud.

```bash
# Replace ${PROJECT_ID} and ${SERVICE_ACCOUNT_NAME} with your values.
SERVICE_ACCOUNT_NAME="github-actions-service-account"

gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
  --description="Service account for GitHub Actions" \
  --display-name="GitHub Actions Service Account" \
  --project=${PROJECT_ID}
```

### Step 6: Assign Roles to the Service Account
Grant the necessary roles to the newly created service account to allow it to access resources such as Secret Manager.

```bash
# Replace ${PROJECT_ID} and ${SERVICE_ACCOUNT_NAME} with your values.
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 7: Configure GitHub Actions to Authenticate

Use the extracted value as the `workload_identity_provider` value in your GitHub Actions YAML.

```yaml
name: Deploy to Google Cloud and Test Earth Engine Script

on:
  workflow_dispatch:
  push:
    branches:
      - '**'  # To execute on all branches

permissions:
  id-token: write       # Allows generating OIDC tokens
  contents: read        # Default read access to repository contents

jobs:
  deploy-and-test:
    runs-on: ubuntu-latest

    steps:
      # 1. Checkout the repository
      - name: Checkout repository
        uses: actions/checkout@v4

      # 2. Authenticate to Google Cloud using Workload Identity Federation
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          token_format: 'access_token'
          workload_identity_provider: ${{ secrets.WORKLOAD_IDENTITY_PROVIDER }}
          project_id: ${{ secrets.GCP_PROJECT_ID }}

      # 3. Silent Authentication Verification
      - name: Silent Authentication Verification
        run: |
          # Confirm authentication is successful by listing gcloud accounts
          gcloud auth list --filter=status:ACTIVE --format="value(account)" || exit 1
          
          # Check if project ID is set correctly
          [[ "$(gcloud config get-value project)" == "${{ secrets.GCP_PROJECT_ID }}" ]] || exit 1
          
          # Confirm that gcloud can retrieve project IAM policies, which requires proper permissions
          gcloud projects get-iam-policy "${{ secrets.GCP_PROJECT_ID }}" --format="value(bindings)" > /dev/null || exit 1

      # 4. Configure gcloud project
      - name: Configure gcloud
        run: |
          gcloud config set project "${{ secrets.GCP_PROJECT_ID }}"

      # 5. Create a Secret in Secret Manager
      - name: Create a Secret in Secret Manager
        run: |
          gcloud secrets create "my-secret" \
            --project="${{ secrets.GCP_PROJECT_ID }}" \
            --replication-policy="automatic"

      # 6. Add a Version to the Secret
      - name: Add a Version to the Secret
        run: |
          echo -n "your-secret-value" | gcloud secrets versions add "my-secret" \
            --project="${{ secrets.GCP_PROJECT_ID }}" \
            --data-file=-

      # 7. Grant Permissions to the Workload Identity Pool
      - name: Grant Permissions to the Workload Identity Pool
        run: |
          gcloud secrets add-iam-policy-binding "my-secret" \
            --project="${{ secrets.GCP_PROJECT_ID }}" \
            --role="roles/secretmanager.secretAccessor" \
            --member="principalSet://iam.googleapis.com/${{ secrets.WORKLOAD_IDENTITY_POOL_ID }}/attribute.repository/\$\{\{ env.REPOSITORY \}\}"

      # 8. Set up Python
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'  # Specify the Python version you need

      # 9. Install dependencies
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install earthengine-api

      # 10. Run Earth Engine Script
      - name: Run Earth Engine Script
        run: |
          python test.py

      # 11. Deploy Application to App Engine
      - name: Deploy Application to App Engine
        run: |
          gcloud app deploy --quiet
```

**Note**: The `project_id` input is optional but may be required by some downstream systems such as `gcloud` CLI.

### Step 8: Create GitHub Secrets

To configure the GitHub Actions workflow to work properly, you need to add the following secrets to your GitHub repository. These secrets can be added in your repository's settings, under **Settings > Secrets and variables > Actions**.

#### Required Secrets
1. **`WORKLOAD_IDENTITY_PROVIDER`**
   - **Value**: The full resource name of the workload identity provider you obtained in **Step 4**. For example:
     ```
     projects/123456789/locations/global/workloadIdentityPools/github/providers/my-repo
     ```

2. **`GCP_PROJECT_ID`**
   - **Value**: The ID of your Google Cloud project. This is the same as the `PROJECT_ID` you used throughout the steps.
     ```
     gitactions-idfederation
     ```

3. **`GCP_SERVICE_ACCOUNT_EMAIL`**
   - **Value**: The email of the Google Cloud service account you created in **Step 5**. For example:
     ```
     github-actions-service-account@your-project-id.iam.gserviceaccount.com
     ```

4. **`YOUR_SECRET_VALUE`**
   - **Value**: The value you added to Google Secret Manager in **Step 6**. For example:
     ```
     my-secret-value
     ```

5. **`WORKLOAD_IDENTITY_POOL_ID`**
   - **Value**: The full resource ID of the workload identity pool you obtained in **Step 2**. For example:
     ```
     projects/123456789/locations/global/workloadIdentityPools/github
     ```

6. **`REPOSITORY`**
   - **Value**: The full name of the GitHub repository, which should be added manually as a secret or environment variable. For example, if the repository URL is:
     ```
     https://github.com/username/earthengine-api-test
     ```
     Then the value should be:
     ```
     username/earthengine-api-test
     ```
     https://github.com/username/earthengine-api-test
     ```
     Then the value should be:
     ```
     username/earthengine-api-test
     ```

To add these secrets:
1. Navigate to your GitHub repository.
2. Go to **Settings > Secrets and variables > Actions**.
3. Click on **New repository secret**.
4. Enter the name (e.g., `WORKLOAD_IDENTITY_PROVIDER`) and the value (e.g., `projects/123456789/...`).
