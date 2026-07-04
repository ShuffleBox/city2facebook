# city2facebook

Generate AI-powered summaries of Denton, TX city government meetings and publish them to a Facebook page.

## How It Works

1. Scans a meeting archive containing `metadata.json`, `whisper_transcript.txt`, and `agenda.pdf` per meeting
2. Sends the full transcript + agenda to a local LLM (llama.cpp) for structured summarization
3. Formats the summary as a Facebook post with key decisions, community impact, and relevant hashtags
4. Publishes to a Facebook Page via the Graph API, tracking posted meetings to avoid duplicates

## Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/city2facebook.git
cd city2facebook

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r city2facebook/requirements.txt

# Copy example config and fill in your values
cp city2facebook/config.example.json city2facebook/config.json
# Edit config.json with your archive path, LLM details, and Facebook credentials
```

### Facebook Page Token

To get a valid page access token:

1. Go to [Facebook Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app, click "Get Token" → "Get User Access Token"
3. Ensure `pages_manage_posts` and `pages_read_engagement` permissions are checked
4. Generate the user token, then call `/me/accounts?fields=id,access_token` in the explorer
5. Copy the `access_token` from your page's entry in the response — this is the **page token**
6. Also note the page `id` from the same response
7. Place both in `config.json`

The page token lasts ~60 days. When it expires, repeat the process.

### LLM Server

The tool expects a local LLM running the OpenAI-compatible API (e.g., llama.cpp):

```bash
./server -m /path/to/model.gguf --port 8000
```

Update `llm_base_url`, `llm_model`, and `llm_key` in `config.json` accordingly.

## Usage

### List meetings in the archive

```bash
python city2facebook/main.py list
python city2facebook/main.py list --search "zoning"
python city2facebook/main.py list --body "City Council"
python city2facebook/main.py list --limit 20
```

### Process a single meeting

**Dry run** (generate summary, don't post):
```bash
python city2facebook/main.py process --meeting-id 108037 --dry-run
```

**Interactive mode** (review before posting):
```bash
python city2facebook/main.py process --meeting-id 108037
# Then choose: [p]ost, [s]kip, or [e]xport draft to file
```

**Auto-post** (generate and publish immediately):
```bash
python city2facebook/main.py process --meeting-id 108037 --auto
```

**Force reprocess** (re-generate and re-post even if already in the posted log):
```bash
python city2facebook/main.py process --meeting-id 108037 --auto --force
```

### Verbose logging

Add `-v` to any command for debug-level output:
```bash
python city2facebook/main.py -v process --meeting-id 108037 --dry-run
```

### Custom config

Use `--config` to point to a different config file (e.g., for local dev):
```bash
python city2facebook/main.py --config config.dev.json process --meeting-id 108037 --dry-run
```

## Archive Structure

Expected directory layout per meeting:
```
archive/
  bag-108037/
    data/
      metadata.json          # Meeting title, date, chapters
      whisper_transcript.txt # Full meeting transcript
      agenda.pdf             # Meeting agenda document
      video.mp4              # (optional, ignored by the tool)
```

## Configuration

| Key | Description |
|---|---|
| `archive_dir` | Path to the root archive directory containing `bag-*` folders |
| `llm_base_url` | Base URL of the OpenAI-compatible LLM server |
| `llm_model` | Name of the model to use |
| `llm_key` | API key for the LLM server |
| `fb_page_id` | Facebook Page numeric ID |
| `fb_token` | Facebook Page Access Token |
| `posted_log` | Path to the JSONL file tracking posted meetings (default: `posted.jsonl`) |

## Project Structure

```
city2facebook/
  main.py            # CLI entry point, argument parsing, workflow orchestration
  meeting.py         # Meeting data loading from archive bags
  extract_agenda.py  # PDF text extraction (PyMuPDF)
  summarizer.py      # LLM prompt building, API call, JSON parsing
  poster.py          # Post formatting, Facebook Graph API, duplicate tracking
  config.example.json # Template config (copy to config.json)
  requirements.txt   # Python dependencies
```

## Performance Notes

- LLM summarization typically takes 3–5 minutes per meeting due to full transcript + agenda context
- Verbose mode (`-v`) logs token counts and generation time
- The `list` command uses optimized directory scanning to handle large archives (1,900+ meetings)
