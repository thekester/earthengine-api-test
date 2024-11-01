# GitHub Actions Authentication with Google Cloud using Direct Workload Identity Federation

This repository demonstrates how to authenticate GitHub Actions workflows to Google Cloud using **Direct Workload Identity Federation**. This setup allows GitHub Actions to securely access Google Cloud resources without the need for long-lived service account keys.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
  - [1. Create a Service Account in Google Cloud](#1-create-a-service-account-in-google-cloud)
  - [2. Create a Workload Identity Pool](#2-create-a-workload-identity-pool)
  - [3. Create a Workload Identity Provider](#3-create-a-workload-identity-provider)
  - [4. Grant Permissions to the Service Account](#4-grant-permissions-to-the-service-account)
  - [5. Grant Access to Google Cloud Resources](#5-grant-access-to-google-cloud-resources)
  - [6. Configure GitHub Actions Workflow](#6-configure-github-actions-workflow)
  - [7. Verify the Service Account Creation](#7-verify-the-service-account-creation)
  - [8. Ensure Correct Project Configuration](#8-ensure-correct-project-configuration)
- [Testing the Configuration](#testing-the-configuration)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)
- [Resources](#resources)

## Prerequisites

Before you begin, ensure you have the following:

1. **Google Cloud Project**: 
   - **Project ID**: `ee-theophileavenel`
   - **Project Number**: `816258773512`

2. **GitHub Repository**:
   - **Repository URL**: [thekester/earthengine-api-test](https://github.com/thekester/earthengine-api-test)

3. **Google Cloud SDK (`gcloud`)**: Installed and configured on your local machine. [Installation Guide](https://cloud.google.com/sdk/docs/install)

4. **Permissions**:
   - Google Cloud account with permissions to create Service Accounts, Workload Identity Pools, and manage IAM roles.

## Setup Instructions

Follow these steps to configure GitHub Actions to authenticate with Google Cloud using Direct Workload Identity Federation.

### 1. Create a Service Account in Google Cloud

The Service Account allows GitHub Actions to interact with Google Cloud resources.

1. **Access the Google Cloud Console**:  
   Navigate to [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts) in your project `ee-theophileavenel`.

2. **Create a New Service Account**:  
   - Click on **"Create Service Account"**.
   - **Name**: `github-actions-earthengine-api-test`
   - **ID**: `github-actions-earthengine-api`
   - **Description**: `Service account for GitHub Actions Workload Identity Federation`
   - Click **"Create and Continue"**.

3. **Assign Roles**:  
   Assign the necessary roles based on your workflow needs. For example:
   - **Secret Manager Secret Accessor** (`roles/secretmanager.secretAccessor`)
   - **Viewer** (`roles/viewer`)

   > **Note**: Apply the principle of least privilege by only granting necessary roles.

4. **Finalize**:  
   - Click **"Done"** to create the Service Account.

5. **Note the Service Account Email**:  
   - Example: `github-actions-earthengine-api-test@ee-theophileavenel.iam.gserviceaccount.com`

### 2. Create a Workload Identity Pool

The Workload Identity Pool allows external identities (like GitHub Actions) to authenticate with Google Cloud.

1. **Open Cloud Shell** or use your terminal with `gcloud` installed.

2. **Create the Workload Identity Pool**:

   ```bash
   gcloud iam workload-identity-pools create "gh-actions-ee-api-pool" \
     --project="ee-theophileavenel" \
     --location="global" \
     --display-name="GitHub Actions EE API Pool"
   ```

3. **Verify the Workload Identity Pool Creation**:  
   Run the following command to verify that the pool was created successfully:

   ```bash
   gcloud iam workload-identity-pools list --project="ee-theophileavenel" --location="global"
   ```

   You should see `gh-actions-ee-api-pool` listed. If not, review any error messages for guidance.

4. **Retrieve the Pool Name**:

   ```bash
   POOL_NAME=$(gcloud iam workload-identity-pools describe "gh-actions-ee-api-pool" \
     --project="ee-theophileavenel" \
     --location="global" \
     --format="value(name)")

   if [ -z "$POOL_NAME" ]; then
     echo "Error: Failed to retrieve Workload Identity Pool Name. Please ensure the pool was created successfully."
     exit 1
   fi

   echo "Workload Identity Pool Name: $POOL_NAME"
   ```

   **Expected Output**:

   ```bash
   projects/816258773512/locations/global/workloadIdentityPools/gh-actions-ee-api-pool
   ```

### 3. Create a Workload Identity Provider

The Workload Identity Provider configures how identities from GitHub Actions are mapped to Google Cloud.

1. **Define GitHub Organization**:
   - GitHub Organization/User: `thekester`

2. **Create the Provider**:

   ```bash
   gcloud iam workload-identity-pools providers create-oidc "gh-actions-ee-api-provider" \
     --project="ee-theophileavenel" \
     --location="global" \
     --workload-identity-pool="gh-actions-ee-api-pool" \
     --display-name="GH Actions EE API Provider" \
     --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
     --attribute-condition="assertion.repository_owner == 'thekester'" \
     --issuer-uri="https://token.actions.githubusercontent.com"
   ```

   > **Note**: The display name was shortened to meet the requirement of being 32 characters or less.

3. **Retrieve the Provider Name**:

   ```bash
   PROVIDER_NAME=$(gcloud iam workload-identity-pools providers describe "gh-actions-ee-api-provider" \
     --project="ee-theophileavenel" \
     --location="global" \
     --workload-identity-pool="gh-actions-ee-api-pool" \
     --format="value(name)")

   if [ -z "$PROVIDER_NAME" ]; then
     echo "Error: Failed to retrieve Workload Identity Provider Name. Please ensure the provider was created successfully."
     exit 1
   fi

   echo "Workload Identity Provider Name: $PROVIDER_NAME"
   ```

   **Expected Output**:

   ```bash
   projects/816258773512/locations/global/workloadIdentityPools/gh-actions-ee-api-pool/providers/gh-actions-ee-api-provider
   ```

### 4. Grant Permissions to the Service Account

Allow the Workload Identity Pool to act as the Service Account.

```bash
gcloud iam service-accounts add-iam-policy-binding "github-actions-earthengine-api-test@ee-theophileavenel.iam.gserviceaccount.com" \
  --project="ee-theophileavenel" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/816258773512/locations/global/workloadIdentityPools/gh-actions-ee-api-pool/attribute.repository/thekester/earthengine-api-test"
```

### 5. Grant Access to Google Cloud Resources

### 5.1. Obtain and Use the Secret Token

In order to access your secret securely, you need to obtain a secret token and set it up in your GitHub repository as a secret environment variable. Here are the steps:

1. **Generate the Access Token from Refresh Token**:
   If you need to obtain an access token to access Google Cloud resources, you can do so by running the following command in your terminal:

   ```bash
   curl -X POST -d "client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&refresh_token=YOUR_REFRESH_TOKEN&grant_type=refresh_token" https://oauth2.googleapis.com/token
   ```

   Replace `YOUR_CLIENT_ID`, `YOUR_CLIENT_SECRET`, and `YOUR_REFRESH_TOKEN` with your actual credentials found in the `~/.config/earthengine/credentials` file.

   The response should contain an access token like this:

   ```json
   {
     "access_token": "ya29.a0AfH6SMBmV...ZLRhDdWdr6X-t5AC23",
     "expires_in": 3600,
     "token_type": "Bearer"
   }
   ```

   Save the `access_token` securely, as you will use it in subsequent steps.

2. **Create a Secret in GitHub**:
   To avoid exposing the `access_token` in your GitHub Actions YAML file, you should create a GitHub secret:

   - Go to your repository on GitHub.
   - Click on **Settings** > **Secrets and variables** > **Actions**.
   - Click on **New repository secret**.
   - Set the **Name** to `GCP_ACCESS_TOKEN` and paste the `access_token` obtained earlier as the **Value**.

3. **Reference the GitHub Secret in the Workflow File**:
   Update your GitHub Actions workflow to use the secret without exposing it directly in the YAML file. You can do so by referencing the secret as follows:

   ```yaml
  name: Deploy to Google Cloud

   on:
   push:
      branches:
         - main

   jobs:
   deploy:
      runs-on: ubuntu-latest
      steps:
         - name: Checkout
         uses: actions/checkout@v3

         - name: Authenticate to Google Cloud
         uses: google-github-actions/auth@v2
         with:
            token_format: 'access_token' # or 'id_token' based on your needs
            workload_identity_provider: 'projects/816258773512/locations/global/workloadIdentityPools/gh-actions-ee-api-pool/providers/gh-actions-ee-api-provider'
            service_account: 'github-actions-earthengine-api-test@ee-theophileavenel.iam.gserviceaccount.com'
            project_id: 'ee-theophileavenel'

         - name: Configure gcloud
         env:
            GCP_ACCESS_TOKEN: ${{ secrets.GCP_ACCESS_TOKEN }}
         run: |
            gcloud config set project "ee-theophileavenel"
            gcloud auth activate-service-account --access-token=$GCP_ACCESS_TOKEN

         # Add your deployment steps here
         - name: Deploy Application
         run: |
            # Your deployment commands   
   ```

   > **Note**: This approach securely accesses the secret token without exposing it directly in your workflow YAML file.

For example, to grant access to Secret Manager:

1. **Ensure Secret Manager API is Enabled**: 
   If the Secret Manager API is not enabled, you may encounter an error indicating that the API is not available. Run the following command to enable it:
   
   ```bash
   gcloud services enable secretmanager.googleapis.com --project="ee-theophileavenel"
   ```
   > **Note**:  and [Secret Manager Pricing](https://cloud.google.com/secret-manager/pricing).

**Possible Error**:

If billing is not enabled for your project, you might encounter the following error:

```
ERROR: (gcloud.services.enable) FAILED_PRECONDITION: Billing account for project '816258773512' is not found. Billing must be enabled for activation of service(s) 'secretmanager.googleapis.com' to proceed.
Reason: UREQ_PROJECT_BILLING_NOT_FOUND
```


2. **Ensure You Have a Secret**:  
   - Example Secret Name: `my-secret`

   **Ensure Secrets Exist in Secret Manager**:
   - If you see "Listed 0 items" after running `gcloud secrets list`, it means no secrets have been created yet. Use the following command to create a secret:

   ```bash
   gcloud secrets create my-secret --replication-policy="automatic" --project="ee-theophileavenel"
   ```

   After creating the secret, try listing again to ensure it's available:

   ```bash
   gcloud secrets list --project="ee-theophileavenel"
   ```

3. **Grant Secret Accessor Role**:

   ```bash
   gcloud secrets add-iam-policy-binding "my-secret" \
     --project="ee-theophileavenel" \
     --role="roles/secretmanager.secretAccessor" \
     --member="principalSet://iam.googleapis.com/projects/816258773512/locations/global/workloadIdentityPools/gh-actions-ee-api-pool/attribute.repository/thekester/earthengine-api-test"
   ```

   > **Note**: Replace `my-secret` with your actual secret name. Repeat this step for each resource GitHub Actions needs to access.
### 6. Configure GitHub Actions Workflow

Update your GitHub Actions workflow to authenticate with Google Cloud using the configured Workload Identity Federation.

1. **Create or Update the Workflow File**:
   - **Path**: `.github/workflows/deploy.yml`

2. **Add the Authentication Step**:

   ```yaml
  # .github/workflows/deploy-and-test.yml

   name: Deploy to Google Cloud and Test Earth Engine Script

   on:
   push:
      branches:
         - main  # Triggers the workflow on pushes to the main branch

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
            service_account: ${{ secrets.GCP_SERVICE_ACCOUNT_EMAIL }}
            project_id: ${{ secrets.GCP_PROJECT_ID }}

         # 3. Configure gcloud
         - name: Configure gcloud
         run: |
            gcloud config set project "${{ secrets.GCP_PROJECT_ID }}"

         # 4. Set up Python
         - name: Set up Python
         uses: actions/setup-python@v5
         with:
            python-version: '3.11'  # Specify the Python version you need

         # 5. Install dependencies
         - name: Install dependencies
         run: |
            python -m pip install --upgrade pip
            pip install earthengine-api

         # 6. Run Earth Engine Script
         - name: Run Earth Engine Script
         run: |
            python test.py

         # 7. Deploy Application to App Engine
         - name: Deploy Application to App Engine
         run: |
            gcloud app deploy --quiet

   ```

   > **Ensure**:
   > - `workload_identity_provider` matches the full name of your Workload Identity Provider.
   > - `service_account` is the email of the Service Account created earlier.
   > - `project_id` is set to your Google Cloud Project ID.

### 7. Verify the Service Account Creation

Run the following command to ensure the service account was created successfully:

```bash
gcloud iam service-accounts list --project=ee-theophileavenel
```

You should see an entry for `github-actions-earthengine-api-test@ee-theophileavenel.iam.gserviceaccount.com`.

### 8. Ensure Correct Project Configuration

Before executing any `gcloud` commands, verify that your `gcloud` is set to the correct project:

```bash
gcloud config get-value project
```

**Expected Output**:

```
ee-theophileavenel
```

If it's not set to `ee-theophileavenel`, set it using:

```bash
gcloud config set project ee-theophileavenel
```

## Testing the Configuration

1. **Push Changes to the main Branch**:  
   Commit and push a change to trigger the workflow.

2. **Monitor GitHub Actions**:  
   Navigate to the **Actions** tab in your GitHub repository.  
   Select the latest workflow run and monitor each step for success.

3. **Verify Access to Google Cloud Resources**:  
   Ensure that GitHub Actions can access the specified Google Cloud resources (e.g., Secret Manager).

## Troubleshooting

If you encounter issues, consider the following steps:

1. **Check GitHub Actions Logs**:  
   Review the logs for any errors or failed steps.

2. **Verify IAM Permissions**:  
   Ensure that the Service Account has the necessary roles.  
   Confirm that IAM policy bindings are correctly set.

3. **Validate Workload Identity Federation Setup**:  
   Ensure that the Workload Identity Pool and Provider are correctly configured.  
   Check that attribute mappings and conditions are accurate.

4. **Test Authentication Manually**:  
   Use `gcloud` commands to manually test authentication if necessary.

5. **Consult Google Cloud Logs**:  
   Check Google Cloud's audit logs for any authentication or authorization errors.

## Security Considerations

- **Least Privilege**: Assign only the necessary roles to the Service Account to minimize security risks.
- **Attribute Conditions**: Ensure that `attribute-condition` in the Workload Identity Provider strictly restricts access to your GitHub repository.
- **Regular Audits**: Periodically review IAM roles and permissions to maintain security integrity.
- **Secret Management**: Use Google Secret Manager to handle sensitive information securely.

> For more details, refer to the **Security Considerations** in the Google Cloud documentation.

## Resources

- [Google Cloud Workload Identity Federation Documentation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [Google GitHub Actions Auth](https://github.com/google-github-actions/auth)
- [Google Cloud SDK Installation Guide](https://cloud.google.com/sdk/docs/install)
- [YAML Validation Tool](https://www.yamllint.com/)
- [Google Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
