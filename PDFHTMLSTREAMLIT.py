import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image
import pytesseract
from openai import OpenAI
from langchain.document_loaders.pdf import PDFMinerPDFasHTMLLoader
from bs4 import BeautifulSoup
import tempfile

# Define the function to extract text from image using pytesseract
def extract_text_from_image(image):
    try:
        text = pytesseract.image_to_string(image)
    except Exception as e:
        text = f"An error occurred during text extraction: {e}"
    return text

# Define the function to load content from PDF
def load_content(uploaded_file, approach):
    content = ""
    if uploaded_file is not None:
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(uploaded_file.read())
                temp_file_path = temp_file.name

            if approach == "Approach 1 with AI":
                content = process_with_ai(temp_file_path)
            elif approach == "Approach 2 Directly":
                content = process_directly(temp_file_path)
        except Exception as e:
            content = f"An error occurred: {e}"
    return content

def process_with_ai(temp_file_path):
    content = ""
    doc = fitz.open(temp_file_path)
    for page_num, page in enumerate(doc, start=1):
        content += f"PAGE {page_num}\n\n"
        content += page.get_text()
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list, start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            img_obj = Image.open(io.BytesIO(image_bytes))
            image_text = extract_text_from_image(img_obj)
            content += image_text
        content += "\n\n----\n\n"
    return content

def process_directly(temp_file_path):
    loader = PDFMinerPDFasHTMLLoader(temp_file_path)
    html_pages = loader.load()
    css_style = """
    <style>
        .centered-content {
            text-align: center;
            margin-left: auto;
            margin-right: auto;
        }
    </style>
    """
    clean_html = css_style  # Start with the CSS
    for page_html in html_pages:
        soup = BeautifulSoup(page_html.page_content, 'html.parser')
        main_content = soup.find('body')
        if main_content:
            main_content['class'] = main_content.get('class', []) + ['centered-content']
        clean_html += soup.prettify() + "\n\n"
    return clean_html

# Define the function to transform text content to HTML
def PDFTOHTML(content, client):
    translated_content = ""
    try:
        pages = content.split("\n\n----\n\n")
        batch_size = 1  # Set your desired batch size here
        for i in range(0, len(pages), batch_size):
            page_group = "\n\n----\n\n".join(pages[i:i + batch_size]).strip()
            if page_group:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo-16k-0613",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You will be tasked with converting text content into HTML format across multiple pages. "
                                "Please use only basic HTML tags like <p>, <h1>, <h2>, and <table> without any styling. "
                                "Ensure that you use these tags to structure the content appropriately. USE UTF-8 encoding. "
                                "For any content that needs to be presented in a table format, "
                                "use the <table>, <tr>, and <td> tags to create the tables. "
                                "Make sure the HTML is simple and only uses these tags for structure. "
                                "Start with the following HTML boilerplate on PAGE 1 only, and do not repeat it for subsequent pages:\n"
                                "<!DOCTYPE html>\n<html>\n<head>\n<title></title>\n</head>\n<body>\n"
                                "Ensure consistent HTML structure and syntax for a valid HTML document."
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Transform this Text to structural HTML: {page_group}. Each page may contain multiple tables. Focus on transforming the different Tables to their correct format they need to be transformed to tables also."
                        }
                    ],
                    max_tokens=8000,
                    temperature=0.5
                )
                response_content = response.choices[0].message.content
                translated_content += response_content
                if i + batch_size < len(pages):
                    translated_content += "\n\n----\n\n"
    except Exception as e:
        translated_content = f"An error occurred during the HTML transformation: {e}"
    return translated_content


# Define the Streamlit UI
def main():
    st.sidebar.title("PDF to HTML Converter")
    api_key = st.sidebar.text_input("Enter your OpenAI API key", type="password")
    approach = st.sidebar.selectbox("Choose your approach", ["Approach 1 with AI", "Approach 2 Directly"])
    uploaded_file = st.sidebar.file_uploader("Upload your PDF here", type=['pdf'])

    st.header("PDF to HTML Converter :bird:")

    if uploaded_file and ((approach == "Approach 1 with AI" and api_key) or approach == "Approach 2 Directly"):
        if st.sidebar.button("Convert PDF"):
            with st.spinner('Processing...'):
                client = OpenAI(api_key=api_key) if approach == "Approach 1 with AI" else None
                content = load_content(uploaded_file, approach)
                if content.startswith("An error occurred"):
                    st.error(content)
                else:
                    if approach == "Approach 1 with AI":
                        html_content = PDFTOHTML(content, client)
                        text_content = content  # If you need to show the original text content.
                    else:
                        html_content = content  # For Approach 2, content is already HTML.
                        text_content = "Text extraction not available in Approach 2."

                    # Display content
                    st.subheader("PDF Content:")
                    if approach == "Approach 1 with AI":
                        st.text_area("Text Content", text_content, height=300)
                    st.subheader("HTML Content Preview:")
                    st.markdown(html_content, unsafe_allow_html=True)

            # Persistent download buttons
            if approach == "Approach 1 with AI":
                 st.sidebar.download_button("Download Text", text_content, file_name="document.txt", mime="text/plain")
            st.sidebar.download_button("Download HTML", html_content, file_name="document.html", mime="text/html")

if __name__ == "__main__":
    main()
