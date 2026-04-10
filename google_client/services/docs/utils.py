from .types import Document

def convert_api_document_to_document(api_doc: dict) -> Document:
    """
    Parses a Google Docs API document representation into a Python dataclass.
    """
    return Document(
        document_id=api_doc.get("documentId", ""),
        title=api_doc.get("title", ""),
        revision_id=api_doc.get("revisionId", "")
    )


def extract_text_from_elements(elements: list) -> str:
    text = ""
    for element in elements:
        if "paragraph" in element:
            for run_element in element["paragraph"].get("elements", []):
                if "textRun" in run_element:
                    text += run_element["textRun"].get("content", "")
        elif "table" in element:
            text += "\n"
            for row in element["table"].get("tableRows", []):
                row_texts = []
                for cell in row.get("tableCells", []):
                    cell_text = extract_text_from_elements(cell.get("content", [])).strip().replace("\n", " ")
                    row_texts.append(cell_text)
                text += "| " + " | ".join(row_texts) + " |\n"
            text += "\n"
    return text

def extract_text_from_document(api_doc: dict) -> str:
    content = api_doc.get("body", {}).get("content", [])
    return extract_text_from_elements(content)

def extract_links_from_elements(elements: list) -> list:
    links = []
    for element in elements:
        if "paragraph" in element:
            for run_element in element["paragraph"].get("elements", []):
                if "textRun" in run_element:
                    style = run_element.get("textRun", {}).get("textStyle", {})
                    if "link" in style and "url" in style["link"]:
                        links.append((run_element["textRun"].get("content", "").strip(), style["link"]["url"]))
        elif "table" in element:
            for row in element["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    links.extend(extract_links_from_elements(cell.get("content", [])))
    return links

def extract_links_from_document(api_doc: dict) -> list:
    content = api_doc.get("body", {}).get("content", [])
    return extract_links_from_elements(content)
