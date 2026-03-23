import PyPDF2
import docx
import re
import logging
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.database import get_db_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def extract_text_from_pdf(file_path):

    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
    except PyPDF2.errors.PdfReadError:
        logging.error(f"Could not read PDF file: {file_path}. It might be corrupted or password-protected.")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing PDF file: {file_path}. Error: {e}")
        return None

def extract_text_from_docx(file_path):
    """
    Extracts text from a DOCX file.
    """
    try:
        doc = docx.Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing DOCX file: {file_path}. Error: {e}")
        return None

def clean_text(text):
    """
    Cleans the extracted text.
    """
    # Remove extra whitespaces
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters (optional, depends on requirements)
    # text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text.strip()

def parse_resume(file_path, user_id):
    """
    Parses a resume file, extracts text, and stores it in the database.
    On re-upload, deletes old entries and inserts new one.
    """
    file_extension = os.path.splitext(file_path)[1].lower()
    extracted_text = None

    if file_extension == '.pdf':
        extracted_text = extract_text_from_pdf(file_path)
    elif file_extension == '.docx':
        extracted_text = extract_text_from_docx(file_path)
    else:
        logging.warning(f"Unsupported file format: {file_extension}")
        return None

    if extracted_text:
        cleaned_text = clean_text(extracted_text)
        
        # Store the extracted text in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Delete old resume analysis entries for this user (re-upload scenario)
            cursor.execute("DELETE FROM resume_analysis WHERE user_id = ?", (user_id,))
            
            # Insert new extracted text
            cursor.execute(
                "INSERT INTO resume_analysis (user_id, extracted_text) VALUES (?, ?)",
                (user_id, cleaned_text)
            )
            conn.commit()
            logging.info(f"Successfully extracted and stored resume text for user_id: {user_id}")
            return cleaned_text
        except Exception as e:
            logging.error(f"Failed to store extracted text for user_id: {user_id}. Error: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()
    else:
        logging.warning(f"Could not extract text from file: {file_path}")
        return None
