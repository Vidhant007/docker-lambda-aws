import logging
import os
import requests
import fitz  # PyMuPDF
import spacy
import re

# Initialize spaCy
nlp = spacy.blank("en")
nlp.add_pipe("sentencizer")

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Define constants
PDF_URL = "http://pressbooks.oer.hawaii.edu/humannutrition2/open/download?type=pdf"
PDF_PATH = "/tmp/human-nutrition-text.pdf"
NUM_SENTENCE_CHUNK_SIZE = 10
MIN_TOKEN_LENGTH = 30

def download_pdf(url: str, filepath: str):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filepath, "wb") as file:
            file.write(response.content)
        logger.info(f"File has been downloaded: {filepath}")
    else:
        logger.error(f"Failed to download file: {filepath}")
        raise Exception(f"Failed to download file: {filepath}")

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

def handler(event, context):
    if not os.path.exists(PDF_PATH):
        logger.info(f"File does not exist, downloading...")
        download_pdf(PDF_URL, PDF_PATH)
    else:
        logger.info(f"File {PDF_PATH} exists")

    pages_and_texts = open_and_read_pdf(PDF_PATH)
    pages_and_texts = process_text_with_spacy(pages_and_texts)
    pages_and_texts = chunk_sentences(pages_and_texts)
    pages_and_chunks = create_chunks(pages_and_texts)
    filtered_chunks = filter_chunks_by_token_length(pages_and_chunks, MIN_TOKEN_LENGTH)

    # Log the filtered chunks
    logger.info(f"Filtered chunks: {filtered_chunks}")

    return {
        'statusCode': 200,
        'body': filtered_chunks
    }
