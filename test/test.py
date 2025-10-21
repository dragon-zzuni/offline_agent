# azure_openai_sample.py
# Requirements: pip install openai python-dotenv
# .env must define:
#   AZURE_OPENAI_ENDPOINT="https://<your-resource>.openai.azure.com/"
#   AZURE_OPENAI_API_KEY="<your-key>"
#   AZURE_OPENAI_DEPLOYMENT="<your-deployment-name>"
#   AZURE_OPENAI_API_VERSION="2024-12-01-preview"  # optional

import os
import sys
from dotenv import load_dotenv
from openai import AzureOpenAI

def require(env_key: str) -> str:
    v = os.getenv(env_key)
    if not v:
        raise RuntimeError(f"Missing required environment variable: {env_key}")
    return v

def main() -> None:
    load_dotenv()

    endpoint = require("AZURE_OPENAI_ENDPOINT")
    api_key = require("AZURE_OPENAI_KEY")
    deployment = "gpt-5"
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview")

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version,
    )

    try:
        resp = client.chat.completions.create(
            model=deployment,  # use your Azure *deployment name*
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello from Azure OpenAI in Korea Central."},
            ]
        )
        print(resp.choices[0].message.content)

        # # print available models (deployments)
        # print("\nAvailable models (deployments):")
        # models = client.models.list()
        # for model in models:
        #     print(f" - {model.id}")
    except Exception as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        # AzureOpenAI doesn't require explicit close, but keeping symmetry if you later stream.
        try:
            client.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()

