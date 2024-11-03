import ee
import os
from google.oauth2 import service_account

# Retrieve the path to the credentials file from the environment variable
credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

if not credentials_path:
    raise EnvironmentError("The environment variable GOOGLE_APPLICATION_CREDENTIALS is not set.")

# Create the credentials object
credentials = service_account.Credentials.from_service_account_file(credentials_path)

# Initialize Earth Engine with the credentials
ee.Initialize(credentials)

# Example script
print(ee.String("Greetings from the Earth Engine servers!").getInfo())

# Test: Elevation of Mount Everest
dem = ee.Image('USGS/SRTMGL1_003')
xy = ee.Geometry.Point([86.9250, 27.9881])
elev = dem.sample(xy, 30).first().get('elevation').getInfo()
print('Mount Everest elevation (m):', elev)

# Verification
assert elev > 0, "Error: Elevation should be a positive number."

print("Test passed: The elevation of Mount Everest was retrieved successfully.")
