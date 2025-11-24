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

### Getting a Facebook access token

You can generate a short-lived user access token with the **Graph API Explorer**:

1. Visit https://developers.facebook.com/tools/explorer/ while signed in to the Facebook account that has access to the target group.
2. Choose your app in the "Meta App" dropdown (or create one if you don't have it yet).
3. Click **Get Token → Get User Access Token** and approve the login dialog.
4. In the permission picker, add the scopes your group requires (for example, `groups_access_member_info` to read group content).
5. Click **Generate Access Token** and copy the resulting token into `FB_ACCESS_TOKEN` or pass it via `--access-token`.

Tokens from the explorer expire quickly; for longer use, create a system user in your app and exchange the short-lived token for a long-lived one via the Graph API.

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
