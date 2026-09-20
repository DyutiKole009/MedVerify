"""
check_bedrock_access.py
Run: .venv\Scripts\python.exe scripts\check_bedrock_access.py
"""
import sys, os
from pathlib import Path

env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)

import boto3

REGION = os.getenv("AWS_REGION", "us-east-1")
KEY    = os.getenv("AWS_ACCESS_KEY_ID")
SECRET = os.getenv("AWS_SECRET_ACCESS_KEY")
TOKEN  = os.getenv("AWS_SESSION_TOKEN") or None

client = boto3.client(
    "bedrock-runtime",
    region_name=REGION,
    aws_access_key_id=KEY,
    aws_secret_access_key=SECRET,
    aws_session_token=TOKEN,
)

MODELS = [
    ("amazon.nova-micro-v1:0",  "Nova Micro  -- orchestrator / routing"),
    ("amazon.nova-lite-v1:0",   "Nova Lite   -- synthesis / vision"),
    ("amazon.nova-pro-v1:0",    "Nova Pro    -- deep agent"),
    ("amazon.nova-2-lite-v1:0", "Nova 2 Lite -- next-gen lite"),
]

TEST_MSG = [{"role": "user", "content": [{"text": "hi"}]}]

print(f"\n{'='*60}")
print(f"  Bedrock model access check  |  region: {REGION}")
print(f"{'='*60}\n")

ok_models  = []
err_models = []

for model_id, label in MODELS:
    try:
        resp = client.converse(
            modelId=model_id,
            messages=TEST_MSG,
            inferenceConfig={"maxTokens": 10},
        )
        reply = resp["output"]["message"]["content"][0]["text"]
        print(f"  OK  {model_id:<42}  AUTHORIZED")
        print(f"      ({label})")
        print(f"      reply: {reply!r}\n")
        ok_models.append(model_id)
    except Exception as e:
        err_str = str(e)
        if "Operation not allowed" in err_str:
            print(f"  XX  {model_id:<42}  NOT ENABLED (model access off)")
        else:
            print(f"  ??  {model_id:<42}  {type(e).__name__}: {err_str[:60]}")
        print(f"      ({label})\n")
        err_models.append(model_id)

print(f"{'='*60}")
print(f"  Results: {len(ok_models)} authorized, {len(err_models)} blocked")
print(f"{'='*60}\n")

if err_models:
    print("  ACTION REQUIRED -- cannot be fixed via SDK, must use console:")
    print(f"  https://{REGION}.console.aws.amazon.com/bedrock/home?region={REGION}#/modelaccess\n")
    print("  Steps:")
    print("  1. Open the URL above")
    print("  2. Click 'Modify model access'")
    print("  3. Tick these models:")
    for m in err_models:
        print(f"       [ ]  {m}")
    print("  4. Click 'Save changes'")
    print("  5. Re-run this script to confirm\n")
else:
    print("  All models authorized. Ready.\n")

print("  Current .env model assignments:")
for var in ["BEDROCK_ORCHESTRATOR_MODEL_ID", "BEDROCK_SYNTHESIS_MODEL_ID",
            "BEDROCK_VISION_MODEL_ID", "BEDROCK_DEEP_AGENT_MODEL_ID"]:
    val = os.getenv(var, "(not set)")
    tag = "OK" if val in ok_models else ("XX" if val in err_models else " ?")
    print(f"  [{tag}]  {var} = {val}")
print()
