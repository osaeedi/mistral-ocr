#!/usr/bin/env python3
import os
import json
from dotenv import load_dotenv
from mistralai import Mistral
from parse import compile as parse_compile

def replace_images(json_blob):
    """Replaces image references in the markdown with inline <img> tags."""
    p = parse_compile("![{img_id1}]({img_id2})")
    names = [
        match['img_id1']
        for match in p.findall(json_blob["markdown"])
        if match['img_id1'] == match['img_id2']
    ]
    for name in names:
        for img in json_blob["images"]:
            if name in img["id"]:
                # replace e.g. ![img123](img123) with inline <img src="data:image..." />
                md_ref = f"![{name}]({name})"
                image_html = f'<img src="{img["image_base64"]}"/>'
                json_blob["markdown"] = json_blob["markdown"].replace(md_ref, image_html)
    return json_blob

def page_to_markdown(page):
    """Extract a page's markdown (with images replaced) from the OCR result."""
    json_blob = json.loads(page.model_dump_json())
    replaced = replace_images(json_blob)
    return replaced["markdown"]

def main():
    # Load MISTRAL_API_KEY from .env or environment
    load_dotenv()
    api_key = os.environ["MISTRAL_API_KEY"]

    # Initialize the Mistral client
    client = Mistral(api_key=api_key)

    # Read the PDF file from disk
    pdf_filename = "Regierungsratsbeschluss.pdf"
    with open(pdf_filename, "rb") as f:
        pdf_bytes = f.read()

    # Upload the file for OCR
    uploaded_pdf = client.files.upload(
        file={
            "file_name": pdf_filename,
            "content": pdf_bytes,
        },
        purpose="ocr"
    )

    # Get a signed URL for the uploaded file
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)

    # Run OCR on the uploaded PDF
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        include_image_base64=True,
        document={
            "type": "document_url",
            "document_url": signed_url.url,
        }
    )

    # Combine all pages' markdown into one string
    all_pages_markdown = []
    for page in ocr_response.pages:
        all_pages_markdown.append(page_to_markdown(page))
    combined_markdown = "\n\n".join(all_pages_markdown)

    # Write the final markdown to a file
    output_filename = "Regierungsratsbeschluss.md"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(combined_markdown)

    print(f"Done! Saved OCR results to {output_filename}")

if __name__ == "__main__":
    main()
