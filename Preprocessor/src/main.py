import logging
import os
import fitz  # PyMuPDF
import spacy
import re
import boto3
import json

# Initialize spaCy
nlp = spacy.blank("en")
nlp.add_pipe("sentencizer")

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Define constants
NUM_SENTENCE_CHUNK_SIZE = 10
MIN_TOKEN_LENGTH = 30
SECOND_LAMBDA_NAME = "arn:aws:lambda:ap-south-1:808300628517:function:Chunk-Embedder"
AWS_REGION = "ap-south-1"
S3_BUCKET_NAME = "rag-chunk-storage"
FILTERED_CHUNKS_FILE_KEY = "filtered_chunks.json"

def download_from_s3(bucket: str, key: str, download_path: str):
    s3 = boto3.client('s3', region_name=AWS_REGION)
    s3.download_file(bucket, key, download_path)
    logger.info(f"File downloaded from S3: s3://{bucket}/{key} to {download_path}")

def text_formatter(text: str) -> str:
    return text.replace("\n", " ").strip()

def open_and_read_pdf(pdf_path: str) -> list:
    doc = fitz.open(pdf_path)
    pages_and_texts = []
    for page_number, page in enumerate(doc):
        text = page.get_text()
        text = text_formatter(text=text)
        pages_and_texts.append({
            "page_number": page_number,
            "page_char_count": len(text),
            "page_word_count": len(text.split(" ")),
            "page_sentence_count_raw": len(text.split(". ")),
            "page_token_count": len(text) / 4,
            "text": text
        })
    return pages_and_texts

def process_text_with_spacy(pages_and_texts):
    for item in pages_and_texts:
        doc = nlp(item["text"])
        item["sentences"] = [str(sent) for sent in doc.sents]
        item["page_sentence_count_spacy"] = len(item["sentences"])
    return pages_and_texts

def split_list(input_list: list, slice_size: int) -> list:
    return [input_list[i:i + slice_size] for i in range(0, len(input_list), slice_size)]

def chunk_sentences(pages_and_texts):
    for item in pages_and_texts:
        item["sentence_chunks"] = split_list(item["sentences"], NUM_SENTENCE_CHUNK_SIZE)
        item["num_chunks"] = len(item["sentence_chunks"])
    return pages_and_texts

def create_chunks(pages_and_texts):
    pages_and_chunks = []
    for item in pages_and_texts:
        for sentence_chunk in item["sentence_chunks"]:
            chunk_dict = {}
            chunk_dict["page_number"] = item["page_number"]
            joined_sentence_chunk = "".join(sentence_chunk).replace("  ", " ").strip()
            joined_sentence_chunk = re.sub(r'\.([A-Z])', r'. \1', joined_sentence_chunk) 
            chunk_dict["sentence_chunk"] = joined_sentence_chunk
            chunk_dict["chunk_char_count"] = len(joined_sentence_chunk)
            chunk_dict["chunk_word_count"] = len(joined_sentence_chunk.split())
            chunk_dict["chunk_token_count"] = len(joined_sentence_chunk) / 4
            pages_and_chunks.append(chunk_dict)
    return pages_and_chunks

def filter_chunks_by_token_length(pages_and_chunks, min_token_length):
    return [chunk for chunk in pages_and_chunks if chunk["chunk_token_count"] > min_token_length]

def upload_to_s3(bucket_name, file_key, data):
    s3 = boto3.client('s3', region_name=AWS_REGION)
    s3.put_object(Bucket=bucket_name, Key=file_key, Body=json.dumps(data))

def invoke_second_lambda_with_s3_trigger():
    lambda_client = boto3.client('lambda', region_name=AWS_REGION)
    lambda_client.invoke(
        FunctionName=SECOND_LAMBDA_NAME,
        InvocationType='Event',  # Asynchronous invocation
        Payload=json.dumps({
            "bucket": S3_BUCKET_NAME,
            "key": FILTERED_CHUNKS_FILE_KEY
        })
    )
    logger.info(f"Second Lambda function triggered with S3 file: s3://{S3_BUCKET_NAME}/{FILTERED_CHUNKS_FILE_KEY}")

def handler(event, context):
    # Log the received event
    logger.info(f"Received event: {event}")

    # Extract bucket and key from the S3 event
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Define the path to save the downloaded PDF
        pdf_path = f"/tmp/{key.split('/')[-1]}"
        
        # Download the PDF from S3
        download_from_s3(bucket, key, pdf_path)

        # Process the PDF
        pages_and_texts = open_and_read_pdf(pdf_path)
        pages_and_texts = process_text_with_spacy(pages_and_texts)
        pages_and_texts = chunk_sentences(pages_and_texts)
        pages_and_chunks = create_chunks(pages_and_texts)
        filtered_chunks = filter_chunks_by_token_length(pages_and_chunks, MIN_TOKEN_LENGTH)

        # Log the filtered chunks
        logger.info(f"Filtered chunks: {filtered_chunks}")

        # Upload filtered chunks to S3
        upload_to_s3(S3_BUCKET_NAME, FILTERED_CHUNKS_FILE_KEY, filtered_chunks)

        # Trigger the second Lambda function with S3 event
        invoke_second_lambda_with_s3_trigger()

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Chunks processed and stored to s3.'})
    }
