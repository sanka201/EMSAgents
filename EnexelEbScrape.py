import requests

# URL of the login endpoint
login_url = "https://accounts-usa.enel.com/commonauth"

# Payload with the credentials and session data
payload = {
    'username_tmp': 'malakasankaliyanage@gmail.com',
    'password': '3Sssmalaka@',
    'sessionDataKey': '5ba57e2c-3634-4ca6-bc37-04f7c0e1bf58',
    'username': 'malakasankaliyanage@gmail.com',
    'tocommonauth': 'false'
}

# Headers (optional but might be required depending on the server's requirements)
headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    # Add other headers if necessary (e.g., CSRF tokens, Referer, etc.)
}

# Create a session to persist cookies
session = requests.Session()

# Send the POST request to log in
response = session.post(login_url, data=payload, headers=headers)

# Check if the login was successful by inspecting the response or by requesting a page that requires authentication
if response.ok:
    print("Login successful!")
    # Optionally, you can navigate to a different page that requires authentication
    dashboard_url = "https://example.com/dashboard"  # Replace with the actual URL
    dashboard_response = session.get(dashboard_url)
    print(dashboard_response.text)
else:
    print("Login failed. Please check your credentials or payload.")

# Optionally, you can save the session cookies to avoid re-login in the future
# with open('cookies.txt', 'w') as f:
#     for cookie in session.cookies:
#         f.write(f"{cookie.name}={cookie.value}\n")
