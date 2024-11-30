from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import fitz  # PyMuPDF
import os
import logging
from langchain_nvidia_ai_endpoints import ChatNVIDIA

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
PDF_DIRECTORY = r'e:\fmp\pdfs'  # Directory containing all PDFs
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTEXT_LENGTH = 8000  # Maximum context length for API

# PDF mappings
PDF_MAPPINGS = {
    "Indian Divorce Act_Combine.pdf": "THE DIVORCE ACT",
    "Indian Evidence Act.pdf": "THE INDIAN EVIDENCE ACT",
    "Indian Penal Code.pdf": "The Indian Penal Code",
    "Negotiable Instruments Act.pdf": "THE NEGOTIABLE INSTRUMENTS",
    "THE CODE OF CIVIL PROCEDURE.pdf": "THE CODE OF CIVIL PROCEDURE",
    "THE CODE OF CRIMINAL PROCEDURE.pdf": "THE CODE OF CRIMINAL PROCEDURE",
    "The Motor Vehicles Act.pdf": "THE MOTOR VEHICLES ACT"
}

# Initialize Nemotron client
NVIDIA_API_KEY = "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"
client = ChatNVIDIA(
    model="nvidia/nemotron-4-340b-instruct",
    api_key=NVIDIA_API_KEY,
    temperature=0.2,
    top_p=0.7,
    max_tokens=1024,
)

def get_available_pdfs():
    """Get list of available PDFs in the directory with their display names"""
    if not os.path.exists(PDF_DIRECTORY):
        os.makedirs(PDF_DIRECTORY)
    pdfs = [f for f in os.listdir(PDF_DIRECTORY) if f.endswith('.pdf')]
    return [{
        'filename': pdf,
        'display': PDF_MAPPINGS.get(pdf, pdf)
    } for pdf in pdfs]

def get_pdf_path(filename):
    """Get full path for a PDF file"""
    return os.path.join(PDF_DIRECTORY, filename)

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF with better formatting"""
    try:
        doc = fitz.open(pdf_path)
        text = []
        for page in doc:
            text.append(page.get_text())
        doc.close()
        return "\n".join(text)
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise

def truncate_context(context, max_length=MAX_CONTEXT_LENGTH):
    """Truncate context to maximum length while preserving meaning"""
    if len(context) <= max_length:
        return context
    
    # Try to truncate at sentence boundary
    truncated = context[:max_length]
    last_period = truncated.rfind('.')
    if last_period > 0:
        return context[:last_period + 1]
    return truncated + "..."

def query_nemotron(question, context):
    """Process query with improved formatting and error handling"""
    try:
        # Truncate context if too long
        truncated_context = truncate_context(context)
        
        prompt = f"""Based on the following legal document excerpt, please answer the question.

Context: {truncated_context}

Question: {question}

Please provide a detailed answer in bullet points. Each point should be clear and concise. Format your response as:
• Point 1
• Point 2
• Point 3
etc.

If you cannot find relevant information in the context, please say so."""

        messages = [
            {
                "role": "system", 
                "content": "You are a helpful legal assistant that answers questions based on the provided context. Always format your answers in bullet points."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]

        try:
            response = ""
            for chunk in client.stream(messages):
                if chunk and hasattr(chunk, 'content'):
                    response += chunk.content

            # Handle empty response
            if not response.strip():
                logger.warning("Empty response from model")
                return "• No relevant information found in the document."

            # Ensure response starts with bullet points
            cleaned_response = response.strip()
            if not cleaned_response.startswith('•'):
                lines = [line.strip() for line in cleaned_response.split('\n') if line.strip()]
                cleaned_response = '\n'.join(f'• {line}' for line in lines)

            return cleaned_response

        except Exception as api_error:
            logger.error(f"API Error: {str(api_error)}")
            return "• Sorry, I encountered an error while processing your question. Please try again."

    except Exception as e:
        logger.error(f"Model inference failed: {str(e)}")
        raise

@app.route('/pdfs', methods=['GET'])
def list_pdfs():
    """List all available PDFs with display names"""
    try:
        pdfs = get_available_pdfs()
        return jsonify({
            'pdfs': pdfs,
            'count': len(pdfs)
        })
    except Exception as e:
        logger.error(f"Error listing PDFs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/process-pdf/<filename>', methods=['GET'])
def process_pdf(filename):
    """Process a specific PDF"""
    try:
        pdf_path = get_pdf_path(filename)
        if not os.path.exists(pdf_path):
            return jsonify({'error': f'PDF file not found: {filename}'}), 404
        
        text = extract_text_from_pdf(pdf_path)
        
        if not text.strip():
            return jsonify({'error': 'No text could be extracted from the PDF'}), 400
        
        display_name = PDF_MAPPINGS.get(filename, filename)
        logger.info(f"Successfully processed PDF: {display_name}")
        return jsonify({
            'message': 'PDF processed successfully',
            'filename': filename,
            'display': display_name,
            'text': text,
            'text_length': len(text)
        })
            
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/query', methods=['POST'])
def process_query():
    """Process a query about the PDF content"""
    try:
        data = request.json
        question = data.get('question')
        context = data.get('context')

        if not question or not context:
            return jsonify({'error': 'Missing question or context'}), 400

        try:
            answer = query_nemotron(question, context)
            
            if not answer:
                return jsonify({
                    'error': 'No answer generated',
                    'answer': '• Sorry, I could not generate an answer. Please try rephrasing your question.'
                }), 200

            logger.info(f"Successfully processed query: {question[:50]}...")
            return jsonify({
                'answer': answer,
                'question': question,
                'context_length': len(context)
            })
        
        except Exception as model_error:
            logger.error(f"Model error: {str(model_error)}")
            return jsonify({
                'error': 'Error processing question',
                'answer': '• Sorry, I encountered an error. Please try again later.'
            }), 200

    except Exception as e:
        logger.error(f"Query error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Check system health"""
    try:
        pdfs = get_available_pdfs()
        return jsonify({
            'status': 'healthy',
            'pdf_directory': PDF_DIRECTORY,
            'available_pdfs': len(pdfs),
            'pdfs': pdfs
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Create PDF directory if it doesn't exist
    os.makedirs(PDF_DIRECTORY, exist_ok=True)
    
    # Check if directory is empty
    pdfs = get_available_pdfs()
    if not pdfs:
        logger.warning(f"No PDF files found in directory: {PDF_DIRECTORY}")
    else:
        logger.info(f"Found {len(pdfs)} PDF files")
        for pdf in pdfs:
            logger.info(f"- {pdf['display']} ({pdf['filename']})")
    
    app.run(host='0.0.0.0', port=5000, debug=True)