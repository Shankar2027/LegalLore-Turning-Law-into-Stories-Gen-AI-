import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GROQ_API_KEY") # This holds your Gemini key based on our setup

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)

print("✅ Google Models you can use right now:")
for model in response.json().get("models", []):
    # Only print models that support text generation
    if "generateContent" in model.get("supportedGenerationMethods", []):
        print(f"- {model['name'].replace('models/', '')}")