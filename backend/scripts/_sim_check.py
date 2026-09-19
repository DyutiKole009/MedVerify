import boto3, os
from dotenv import load_dotenv
load_dotenv('.env')

# Use bedrock (not bedrock-runtime) to check model entitlement state
bedrock = boto3.client('bedrock',
    region_name='us-east-1',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
)

for model_id in ['amazon.nova-micro-v1:0', 'amazon.nova-lite-v1:0']:
    try:
        r = bedrock.get_foundation_model(modelIdentifier=model_id)
        m = r['modelDetails']
        print(f"Model: {model_id}")
        print(f"  Status          : {m.get('modelLifecycle', {}).get('status')}")
        print(f"  inputModalities : {m.get('inputModalities')}")
        # Check if there's any entitlement field
        for k,v in m.items():
            if 'entitle' in k.lower() or 'access' in k.lower() or 'consent' in k.lower():
                print(f'  {k}: {v}')
        print()
    except Exception as e:
        print(f'{model_id}: {e}')

# List model invocation logging config - might hint at restrictions
try:
    log = bedrock.get_model_invocation_logging_configuration()
    print('Logging config:', log.get('loggingConfig'))
except Exception as e:
    print('Logging config error:', e)
