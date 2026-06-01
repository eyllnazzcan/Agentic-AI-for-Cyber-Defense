from PyPDF2 import PdfReader


def load_pdf(path):
    # Extract text from all readable pages in a PDF file.

    reader = PdfReader(path)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text
