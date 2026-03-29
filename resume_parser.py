import PyPDF2
import docx

def extract_text_from_pdf(path):
    text = ""
    with open(path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text()
    return text.lower()

def extract_text_from_docx(path):
    doc = docx.Document(path)
    return " ".join([para.text for para in doc.paragraphs]).lower()
