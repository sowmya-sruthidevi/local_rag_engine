import requests
import json

url = "http://localhost:8002/ask"
question = "What is the platform for Indian influencers?"

response = requests.post(url, json={"question": question})

print("Status Code:", response.status_code)
print("\nResponse:", json.dumps(response.json(), indent=2))
