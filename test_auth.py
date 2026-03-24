import requests
import sys
import json

KEYCLOAK_URL = "http://localhost:8080/realms/authwebapp/protocol/openid-connect/token"
BACKEND_URL = "http://localhost:8000/api/v1/manifest"

# 1. Get Token from Keycloak
data = {
    "client_id": "authwebapp-frontend",
    "username": "tester",
    "password": "tester",
    "grant_type": "password",
    "client_secret": "keycloak-frontend-secret-change-me"
}

print("Fetching token from Keycloak...")
try:
    response = requests.post(KEYCLOAK_URL, data=data)
    response.raise_for_status()
    token_data = response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        print("No access token in response:", token_data)
        sys.exit(1)
    
    print(f"Token acquired. Length: {len(access_token)}")
    
    # 2. Test Backend API with Token
    print("\nTesting backend API /api/v1/manifest...")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    api_res = requests.get(BACKEND_URL, headers=headers)
    print(f"API Response Status: {api_res.status_code}")
    if api_res.status_code == 200:
        print("API Output:", api_res.text[:200] + "...")
    else:
        print("API Error:", api_res.text)

except Exception as e:
    print(f"Error: {e}")
