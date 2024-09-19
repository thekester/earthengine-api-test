# Earth Engine API Testing with GitHub Actions

This project sets up a GitHub Actions workflow to test the installation and functionality of the Google Earth Engine API using `pip install earthengine-api`. It includes a simple test script (`test.py`) that initializes the API and retrieves the elevation of Mount Everest.

## Prerequisites

- **GitHub Account**: To host the repository and run GitHub Actions workflows.
- **Google Earth Engine Access**: You must have an active Earth Engine account.
- **Git**: For cloning the repository and pushing changes.
- **Earth Engine Python API**: Installed locally to generate credentials.

## Setup Steps

### 1. Clone the Repository

Clone the GitHub repository to your local machine:

\`\`\`bash
git clone https://github.com/thekester/earthengine-api-test.git
cd earthengine-api-test
\`\`\`

### 2. Create the Test Script

Create a file named `test.py` at the root of the project with the following content:

\`\`\`python
import ee

# Initialize the Earth Engine API
ee.Initialize()

# Test the API by retrieving the elevation of Mount Everest
dem = ee.Image('USGS/SRTMGL1_003')
xy = ee.Geometry.Point([86.9250, 27.9881])
elev = dem.sample(xy, 30).first().get('elevation').getInfo()
print('Mount Everest elevation (m):', elev)

# Verify that the elevation is a positive number
assert elev > 0, "Error: Elevation should be a positive number."

print("Test passed: The elevation of Mount Everest was retrieved successfully.")
\`\`\`

### 3. Configure the GitHub Actions Workflow

In the `.github/workflows/` directory, create a file named `main.yml` with the following content:

\`\`\`yaml
name: Earth Engine API Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.8'

    - name: Install dependencies
      run: |
        pip install earthengine-api

    - name: Configure Earth Engine credentials
      env:
        EARTHENGINE_CREDENTIALS: ${{ secrets.EARTHENGINE_CREDENTIALS }}
      run: |
        mkdir -p ~/.config/earthengine
        echo "$EARTHENGINE_CREDENTIALS" > ~/.config/earthengine/credentials

    - name: Run test script
      run: |
        python test.py
\`\`\`

### 4. Obtain Earth Engine Credentials

Generate the credentials file by authenticating locally:

\`\`\`bash
earthengine authenticate
\`\`\`

- Follow the instructions to authorize access.
- A credentials file will be created in the `~/.config/earthengine/` directory.

### 5. Set Up the GitHub Secret

To allow the workflow to access your credentials without exposing them:

1. Access your repository settings on GitHub.
2. Click on "Secrets and variables" in the sidebar, then "Actions".
3. Click on "New repository secret".
4. Name the secret `EARTHENGINE_CREDENTIALS`.
5. Open the file `~/.config/earthengine/credentials` with a text editor.
6. Copy the entire content of the file and paste it into the value field of the secret.
7. Ensure that the JSON includes the `"type": "authorized_user"` field.
8. Save the secret by clicking "Add secret".

Here’s an example image showing how to configure the secret in GitHub:

![Configuring GitHub Secret](configactionsecret.png)

### 6. Commit and Push Changes

Add the files to version control, commit, and push to GitHub:

\`\`\`bash
git add .
git commit -m "Configure Earth Engine API test with GitHub Actions"
git push origin main
\`\`\`

### 7. Verify the Workflow Execution

- Go to the "Actions" tab of your repository on GitHub.
- You should see the workflow "Earth Engine API Test" running.
- Monitor the logs to ensure all steps complete successfully.
- Check the script output to confirm that the elevation of Mount Everest is correctly displayed.

## Important Notes

### Credential Security

- Never commit your credentials or secrets into the source code.
- Always use GitHub Secrets to store sensitive information securely.
- Do not share your credentials in public forums or repositories.

### Credentials File Structure

Ensure that your credentials file has the following structure:

\`\`\`json
{
  "client_id": "your-client-id.apps.googleusercontent.com",
  "client_secret": "your-client-secret",
  "refresh_token": "your-refresh-token",
  "type": "authorized_user"
}
\`\`\`

- The `"type": "authorized_user"` field is mandatory.

### Troubleshooting

- **Authentication Errors**: Verify that the `EARTHENGINE_CREDENTIALS` secret is correctly configured and that the JSON is valid.
- **Dependency Issues**: Ensure that `earthengine-api` is installed correctly.
- **Permission Issues**: Check that your Earth Engine account has the necessary permissions.

## Additional Resources

- [Earth Engine API Documentation](https://developers.google.com/earth-engine)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Secrets Management](https://docs.github.com/en/actions/security-guides/encrypted-secrets)

## Expected Output Example

If everything works correctly, you should see an output similar to the following in the workflow logs:

\`\`\`yaml
Mount Everest elevation (m): 8848
Test passed: The elevation of Mount Everest was retrieved successfully.
\`\`\`