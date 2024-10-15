import ee
import json
import os
import google.oauth2.credentials

# Load credentials from the environment variable
stored = json.loads(os.getenv("EARTHENGINE_TOKEN"))
credentials = google.oauth2.credentials.Credentials(
    None,
    token_uri="https://oauth2.googleapis.com/token",
    client_id=stored["client_id"],
    client_secret=stored["client_secret"],
    refresh_token=stored["refresh_token"],
    quota_project_id=stored["project"],
)

# Initialize the Earth Engine API with the credentials
ee.Initialize(credentials=credentials)

# Print a greeting message from the Earth Engine servers
print(ee.String("Greetings from the Earth Engine servers!").getInfo())

# Test the API: Print the elevation of Mount Everest
dem = ee.Image('USGS/SRTMGL1_003')
xy = ee.Geometry.Point([86.9250, 27.9881])
elev = dem.sample(xy, 30).first().get('elevation').getInfo()
print('Mount Everest elevation (m):', elev)

# Verify that the elevation is a positive number
assert elev > 0, "Error: Elevation should be a positive number."

print("Test passed: The elevation of Mount Everest was retrieved successfully.")
