import re

import requests


def extract_google_id(url):
    """Extracts ID from Google Drive/Docs URLs"""
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
        r"/document/d/([a-zA-Z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_sync_id(url):
    """
    Extracts the 32-character ID from a Notion URL.
    Example: https://.../My-Page-2a5e35723373806abeadddb6143e0912
    Returns: 2a5e35723373806abeadddb6143e0912
    """
    # Regex to find the 32 char hex string at the end of the URL
    match = re.search(r"([a-f0-9]{32})", url)
    if match:
        return match.group(1)
    return None


def fetch_google_content(url):
    """Fetches text from public Google Docs or Drive Files"""
    file_id = extract_google_id(url)
    if not file_id:
        return None

    # 1. Try Export (for Google Docs)
    export_url = f"https://docs.google.com/document/d/{file_id}/export?format=txt"
    response = requests.get(export_url)

    # 2. If not a Doc, try Download (for uploaded .txt/.md)
    if response.status_code != 200:
        download_url = f"https://drive.google.com/uc?id={file_id}&export=download"
        response = requests.get(download_url)

    if response.status_code == 200:
        response.encoding = "utf-8"
        return response.text
    return f"Error: Google Drive status {response.status_code}"


def fetch_notion_content(url):
    """
    Fetches text from a public Notion page.
    Uses the 'notion-api.splitbee.io' public wrapper to turn Notion blocks into JSON.
    """
    page_id = extract_sync_id(url)
    if not page_id:
        return None

    # We use this public API wrapper because Notion's native raw HTML is empty.
    api_url = f"https://notion-api.splitbee.io/v1/page/{page_id}"
    response = requests.get(api_url)

    if response.status_code != 200:
        return f"Error: Notion API status {response.status_code}"

    data = response.json()

    # Iterate through the blocks to reconstruct the text
    full_text = []

    # The JSON is a dictionary of blocks. We generally care about the order.
    # Note: This is a simple parser. It grabs the 'title' property of every block.
    for block_id, block_data in data.items():
        value = block_data.get("value", {})
        properties = value.get("properties", {})

        # 'title' usually holds the text content in a weird format: [["Text", formatting]]
        text_array = properties.get("title", [])

        if text_array:
            # Join the text parts together
            block_text = "".join([t[0] for t in text_array if t])
            full_text.append(block_text)

    return "\n".join(full_text)


def fetch_public_file_content(url):
    """Router to decide which fetcher to use"""
    if "drive.google.com" in url or "docs.google.com" in url:
        print(f"Detected Google URL...")
        return fetch_google_content(url)

    elif "notion.so" in url or "notion.site" in url:
        print(f"Detected Notion URL...")
        return fetch_notion_content(url)

    else:
        return "Error: Unsupported URL format"


# if __name__ == "__main__":
#     it = fetch_public_file_content(
#         "https://drive.google.com/file/d/100vYRNAv5DhB-OfFttplHKsS7lvWPAO4/view?usp=sharing"
#     )
#     print(it)
