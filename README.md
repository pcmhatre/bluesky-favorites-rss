# Bluesky Favorites RSS Feed

Generates an RSS feed from your liked posts on [Bluesky](https://bsky.app), refreshed every 30 minutes via GitHub Actions.

## How it works

A scheduled GitHub Actions workflow authenticates with the Bluesky API, fetches your most recent liked posts, and commits an updated `feed.xml` to this repo. GitHub Pages serves the file as a public URL you can drop into any RSS reader.

## Setup (for your own fork)

### 1. Fork this repo

### 2. Create a Bluesky App Password
Go to **Settings → Privacy and security → App passwords** on Bluesky and generate a new password. Don't use your main account password.

### 3. Add GitHub repository secrets
Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
|---|---|
| `BSKY_HANDLE` | Your handle, e.g. `yourname.bsky.social` |
| `BSKY_APP_PASSWORD` | The app password you just created |

### 4. Enable GitHub Pages
Go to **Settings → Pages** and set the source to **Deploy from a branch → main / root**.

### 5. Trigger the first run
Go to **Actions → Generate RSS Feed → Run workflow**.

Your feed will be live at `https://yourusername.github.io/your-repo-name/feed.xml`.

## Running locally

```bash
cp .env.example .env
# fill in BSKY_HANDLE and BSKY_APP_PASSWORD in .env

pip install -r requirements.txt
python3 generate_feed.py
```

Options:
```
--limit N     Number of liked posts to fetch (default: 100)
--output PATH Output file path (default: feed.xml)
```

## Configuration

| Variable | Where | Description |
|---|---|---|
| `BSKY_HANDLE` | Secret | Your Bluesky handle |
| `BSKY_APP_PASSWORD` | Secret | Bluesky app password |
| `BSKY_FEED_LIMIT` | Repository variable | Posts to fetch (default: 100) |
| `OUTPUT_FILE` | Local `.env` | Output path (default: `feed.xml`) |
