import json
import redis
import os

# Redis connection parameters
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Initialize Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def lambda_handler(event, context):
    try:
        # Example event data
        document_id = event['document_id']
        embedding = event['embedding']
        
        # Store embedding in Redis
        redis_client.hset("embeddings", document_id, json.dumps(embedding))
        
        return {
            'statusCode': 200,
            'body': json.dumps('Embedding stored successfully.')
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
