# Google Docs API Service

The Google Docs service wrapper provides a synchronous and asynchronous interface to create, read, and batch update Google Documents.

## Basic Usage (Synchronous)

```python
from google_client.api_service import APIServiceLayer

# Assuming `user_info` contains valid OAuth2 credentials
api = APIServiceLayer(user_info)

# Create a new document
new_doc = api.docs.create_document("My AI Generated Report")
print(f"Created Document ID: {new_doc.document_id}")

# Fetch document metadata
doc = api.docs.get_document(new_doc.document_id)
print(f"Title: {doc.title}")

# Perform batch updates effortlessly
update_response = (
    api.docs.batch_updater(doc.document_id)
    .insert_text("Hello World!\\n", index=1)
    .insert_text("This is an automated line.\\n", index=14)
    .replace_all_text(contains_text="World", replace_text="Universe")
    .execute()
)
print("Updated successfully!")
```

## Basic Usage (Asynchronous)

For high-performance, non-blocking scenarios:

```python
import asyncio
from google_client.api_service import APIServiceLayer

async def main():
    api = APIServiceLayer(user_info)

    # Note the .async_docs attribute!
    new_doc = await api.async_docs.create_document("Async Generated Report")

    # Perform batch updates in a non-blocking threadpool
    update_response = await (
        api.async_docs.batch_updater(new_doc.document_id)
        .insert_text("Async Hello World!\\n", index=1)
        .replace_all_text(contains_text="World", replace_text="Universe")
        .execute()
    )
    print("Async update applied!")

asyncio.run(main())
```

## Supported Batch Updates
The underlying `DocsBatchUpdater` supports chaining the following methods. For convenience, these are also mapped directly to `api.docs.*` and `api.async_docs.*`.
* `insert_text(text: str, index: int)`
* `delete_text(start_index: int, end_index: int)`
* `replace_all_text(contains_text: str, replace_text: str, match_case: bool)`
* `update_text_style(start_index: int, end_index: int, bold: bool, italic: bool, font_family: str, font_size: int)`
* `update_paragraph_alignment(start_index: int, end_index: int, alignment: str)`
* `update_heading_style(start_index: int, end_index: int, heading_id: str)`
* `insert_page_break(index: int)`
* `insert_table(rows: int, columns: int, index: int)`

## Reading & Extraction
The Google Docs API normally represents content as a deeply nested, abstract syntax tree (`structuralElements`, `paragraphs`, `textRuns`). To simplify interacting with data, especially for AI agents, we provide utilities that flatten this tree:
* `get_document_text(document_id)`: Recursively extracts and returns the entire plain-text payload of the document.
* `get_document_links(document_id)`: Extracts all URLs and their associated anchor text as a list of `tuples`.

## AI Agent Helpers
Because predicting JSON offsets in a dynamic document AST is almost impossible for an LLM agent, we have built the following wrapper abstracts:
* `insert_table_with_data(document_id, index, data: List[List[str]])`: Automatically creates a table, retrieves the dynamically assigned indices, backwards-iterates properties, and executes sequential payload formatting so documents don't become irreparably corrupted by index shifts.
