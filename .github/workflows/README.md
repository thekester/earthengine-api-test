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
   - **ID**: `github-actions-earthengine-api-test`
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
   gcloud iam workload-identity-pools create "github-actions-earthengine-api-test-pool" \
     --project="ee-theophileavenel" \
     --location="global" \
     --display-name="GitHub Actions EarthEngine API Test Pool"
   ```

3. **Retrieve the Pool Name**:

   ```bash
   POOL_NAME=$(gcloud iam workload-identity-pools describe "github-actions-earthengine-api-test-pool" \
     --project="ee-theophileavenel" \
     --location="global" \
     --format="value(name)")

   echo "Workload Identity Pool Name: $POOL_NAME"
   ```

   **Expected Output**:

   ```bash
   projects/816258773512/locations/global/workloadIdentityPools/github-actions-earthengine-api-test-pool
   ```

### 3. Create a Workload Identity Provider

The Workload Identity Provider configures how identities from GitHub Actions are mapped to Google Cloud.

1. **Define GitHub Organization**:
   - GitHub Organization/User: `thekester`

2. **Create the Provider**:

   ```bash
   gcloud iam workload-identity-pools providers create-oidc "github-actions-earthengine-api-test-provider" \
     --project="ee-theophileavenel" \
     --location="global" \
     --workload-identity-pool="github-actions-earthengine-api-test-pool" \
     --display-name="GitHub Actions EarthEngine API Test Provider" \
     --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
     --attribute-condition="assertion.repository_owner == 'thekester'" \
     --issuer-uri="https://token.actions.githubusercontent.com"
   ```

3. **Retrieve the Provider Name**:

   ```bash
   PROVIDER_NAME=$(gcloud iam workload-identity-pools providers describe "github-actions-earthengine-api-test-provider" \
     --project="ee-theophileavenel" \
     --location="global" \
     --workload-identity-pool="github-actions-earthengine-api-test-pool" \
     --format="value(name)")

   echo "Workload Identity Provider Name: $PROVIDER_NAME"
   ```

   **Expected Output**:

   ```bash
   projects/816258773512/locations/global/workloadIdentityPools/github-actions-earthengine-api-test-pool/providers/github-actions-earthengine-api-test-provider
   ```

### 4. Grant Permissions to the Service Account

Allow the Workload Identity Pool to act as the Service Account.

```bash
gcloud iam service-accounts add-iam-policy-binding "github-actions-earthengine-api-test@ee-theophileavenel.iam.gserviceaccount.com" \
  --project="ee-theophileavenel" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/816258773512/locations/global/workloadIdentityPools/github-actions-earthengine-api-test-pool/attribute.repository/thekester/earthengine-api-test"
```

### 5. Grant Access to Google Cloud Resources

For example, to grant access to Secret Manager:

1. **Ensure You Have a Secret**:  
   - Example Secret Name: `my-secret`

2. **Grant Secret Accessor Role**:

   ```bash
   gcloud secrets add-iam-policy-binding "my-secret" \
     --project="ee-theophileavenel" \
     --role="roles/secretmanager.secretAccessor" \
     --member="principalSet://iam.googleapis.com/projects/816258773512/locations/global/workloadIdentityPools/github-actions-earthengine-api-test-pool/attribute.repository/thekester/earthengine-api-test"
   ```

   > **Note**: Replace `my-secret` with your actual secret name. Repeat this step for each resource GitHub Actions needs to access.

### 6. Configure GitHub Actions Workflow

Update your GitHub Actions workflow to authenticate with Google Cloud using the configured Workload Identity Federation.

1. **Create or Update the Workflow File**:
   - **Path**: `.github/workflows/deploy.yml`

2. **Add the Authentication Step**:

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
             workload_identity_provider: 'projects/816258773512/locations/global/workloadIdentityPools/github-actions-earthengine-api-test-pool/providers/github-actions-earthengine-api-test-provider'
             service_account: 'github-actions-earthengine-api-test@ee-theophileavenel.iam.gserviceaccount.com'
             project_id: 'ee-theophileavenel'

         - name: Configure gcloud
           run: |
             gcloud config set project "ee-theophileavenel"
             gcloud auth configure-docker

         # Add your deployment steps here
         - name: Deploy Application
           run: |
             # Your deployment commands
   ```

   > **Ensure**:
   > - `workload_identity_provider` matches the full name of your Workload Identity Provider.
   > - `service_account` is the email of the Service Account created earlier.
   > - `project_id` is set to your Google Cloud Project ID.

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
