import ee

# Initialize the Earth Engine API
ee.Initialize()

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
