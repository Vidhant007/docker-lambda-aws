import json
import redis
import os

# Redis connection parameters
REDIS_HOST = os.getenv('REDIS_HOST')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Initialize Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def handler(event, context):
    try:
        # Example event data
        document_id = event['document_id']
        embedding = event['embedding']
        
        # Store embedding in Redis
        redis_client.hset("embeddings", document_id, json.dumps(embedding))
        
        # Retrieve and print the stored embedding from Redis
        stored_embedding = redis_client.hget("embeddings", document_id)
        print(f"Stored embedding for document_id {document_id}: {stored_embedding}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Embedding stored successfully.',
                'stored_embedding': json.loads(stored_embedding) if stored_embedding else None
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
