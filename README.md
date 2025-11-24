# getComment

Export Facebook group comments to CSV using the Graph API.

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Obtain a Facebook user access token with permissions to read the target group's posts and comments.
3. Export the token so the CLI can read it by default:
   ```bash
   export FB_ACCESS_TOKEN="<YOUR_TOKEN>"
   ```

## Usage
Run the CLI to pull comments from a group and save them to a CSV file:
```bash
python get_comments.py --group-id <GROUP_ID> --output comments.csv
```

Useful options:
- `--since` / `--until`: Restrict posts by timestamp (ISO8601 or Unix epoch).
- `--max-posts`: Cap the number of posts fetched from the group feed.
- `--access-token`: Override the token passed via `FB_ACCESS_TOKEN`.

Each CSV row includes the post metadata plus the comment author, message, like count, and reply count for easier downstream analysis.
