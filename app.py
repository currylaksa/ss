import streamlit as st
import re
import io
from datetime import datetime
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# --- Helper Functions (Adapted from your original script) ---

def extract_info(pdf_file):
    """Extracts Subcon and Receiver name from the PDF file object."""
    try:
        # pypdf can read directly from the uploaded file object
        reader = PdfReader(pdf_file)
        page = reader.pages[0]
        text = page.extract_text()
        
        # Regex to find Subcon
        subcon_match = re.search(r"(?:Subon|Subcon):\s*(.*?)\s*Site Receiver:", text, re.IGNORECASE | re.DOTALL)
        
        subcon = "Unknown"
        if subcon_match:
            subcon = subcon_match.group(1).strip()
            subcon = subcon.replace('\n', ' ')

        # Regex to find Receiver
        receiver_match = re.search(r"Site Receiver:\s*(.*?)(?:/|\d{8,})", text, re.IGNORECASE)
        
        receiver = "Unknown"
        if receiver_match:
            receiver = receiver_match.group(1).strip()

        return subcon, receiver

    except Exception as e:
        st.error(f"Error extracting info: {e}")
        return None, None

def create_overlay(subcon, receiver, date_str):
    """Creates a PDF overlay with the extracted info using ReportLab."""
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    
    # 1. Subcon Logic
    words = subcon.split()
    line1 = ""
    line2 = ""
    
    # Check for "SDN" to split lines
    sdn_index = -1
    for i, word in enumerate(words):
        if "SDN" in word.upper():
            sdn_index = i
            break

    if sdn_index != -1:
        line1_words = words[:sdn_index]
        line2_words = words[sdn_index:]
        
        while len(" ".join(line1_words)) > 30 and len(line1_words) > 1:
            line2_words.insert(0, line1_words.pop())
            
        line1 = " ".join(line1_words)
        line2 = " ".join(line2_words)
    elif len(words) > 2:
        mid = len(words) // 2 + 1
        line1 = " ".join(words[:mid])
        line2 = " ".join(words[mid:])
    else:
        line1 = subcon
        line2 = ""

    # Font size adjustment
    font_size = 6
    if "UNIVERSAL CELLULAR" in subcon.upper() or len(line1) > 30:
        font_size = 4.5
    
    can.setFont("Helvetica", font_size)

    # Coordinates
    can.drawString(510, 742, line1)
    if line2:
        can.drawString(510, 732, line2)

    # 2. Signature Logic
    first_name = receiver.split()[0] if receiver else ""
    first_name = first_name.capitalize()
    
    can.setFont("Times-Italic", 14)
    can.drawString(520, 665, first_name)

    # 3. Date
    can.setFont("Helvetica", 10)
    can.drawString(500, 642, date_str)
    
    can.save()
    packet.seek(0)
    return packet

# --- Main Streamlit Application ---

def main():
    st.set_page_config(page_title="Auto-Sign PDF", layout="centered")

    # --- HIDE STREAMLIT STYLE ---
    hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
    st.markdown(hide_st_style, unsafe_allow_html=True)
    
    st.title("📝 SS")
    st.write("Upload a Delivery Note/POD PDF to automatically sign the Subcon, Receiver Name, and Date.")

    # 1. File Uploader
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    if uploaded_file is not None:
        with st.spinner('Processing...'):
            # 2. Extract Info
            # IMPORTANT: Reset pointer to start of file before reading
            uploaded_file.seek(0)
            subcon, receiver = extract_info(uploaded_file)
            
            if subcon and receiver:
                st.success(f"✅ Found **{subcon}** | Receiver: **{receiver}**")
                
                # 3. Create Overlay & Merge
                current_date = datetime.now().strftime("%d/%m/%Y")
                overlay_packet = create_overlay(subcon, receiver, current_date)
                
                # Reset file pointer again for merging
                uploaded_file.seek(0)
                existing_pdf = PdfReader(uploaded_file)
                new_pdf = PdfReader(overlay_packet)
                output = PdfWriter()

                # Merge first page
                page = existing_pdf.pages[0]
                page.merge_page(new_pdf.pages[0])
                output.add_page(page)

                # Add remaining pages
                for i in range(1, len(existing_pdf.pages)):
                    output.add_page(existing_pdf.pages[i])

                # 4. Save to Memory Buffer
                output_buffer = io.BytesIO()
                output.write(output_buffer)
                output_buffer.seek(0)

                # Generate new filename
                original_name = uploaded_file.name.replace('.pdf', '').replace('.PDF', '')
                timestamp = datetime.now().strftime("%H%M%S")
                new_filename = f"{original_name}_signed_{timestamp}.pdf"

                st.write("---")
                
                # 5. Download Button
                st.download_button(
                    label="Download Signed PDF",
                    data=output_buffer,
                    file_name=new_filename,
                    mime="application/pdf"
                )
            else:
                st.error("Could not extract Subcon or Receiver information. Please check the PDF format.")

if __name__ == "__main__":

    main()

