# Oreilly PDF Downloader

A tool to download O'Reilly ebooks as PDF format.

## Setup

1. Clone the repository:
   ```bash
   git clone <your-repository-url>
   cd oreilly-pdf-downloader
   ```

2. Set up the environment using uv:
   ```bash
   uv sync
   ```

## How to Use

1. Obtain your O'Reilly session cookie (see instructions below).
2. Store your cookie in a `cookie.json` file (or provide it when prompted).
3. Run the downloader:
   ```bash
   uv run python main.py
   ```
4. Enter the ISBN of the book you want to download when prompted.

## Getting Your Cookie

To download O'Reilly content, you need to provide your session cookie. Follow these steps to extract it:

1. Log in to your O'Reilly account in your web browser.
2. Open the browser's developer tools (usually F12 or right-click → Inspect).
3. Go to the Console tab.
4. Paste and run the following JavaScript code:
   ```javascript
   JSON.stringify(document.cookie.split('; ').reduce((prev, current) => {
       const [name, ...value] = current.split('=');
       prev[name] = value.join('=');
       return prev;
   }, {}));
   ```
5. Copy the output string and save it in `cookie.json`.
   **Note**: Do NOT include the surrounding quotes in the `cookie.json` file.

## Notes

- **Subscription Requirement**: You must have an active O'Reilly Learning subscription to access and download content using this tool.
- Ensure you comply with O'Reilly's Terms of Service when using this tool.
- This tool is for personal use only. **Do NOT** distribute downloaded content.
- **Important Limitation**: This tool currently only supports ebooks that are already in PDF styling. If used to download ebooks with EPUB styling, it may cause broken layout or formatting issues in the resulting PDF.
