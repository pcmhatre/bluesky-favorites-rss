#!/usr/bin/env python3
"""
Generate an RSS feed from your Bluesky liked posts (favorites).

Usage:
    python3 generate_feed.py [--output feed.xml] [--limit 100]

Credentials are read from a .env file or environment variables:
    BSKY_HANDLE        your handle, e.g. yourname.bsky.social
    BSKY_APP_PASSWORD  an App Password (Settings → Privacy → App passwords)
"""

import argparse
import os
import sys
import textwrap
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.dom import minidom

from atproto import Client
from dotenv import load_dotenv

load_dotenv()


def post_url(author_handle: str, uri: str) -> str:
    """Convert an AT URI to a bsky.app URL."""
    rkey = uri.split("/")[-1]
    return f"https://bsky.app/profile/{author_handle}/post/{rkey}"


def truncate(text: str, max_chars: int = 100) -> str:
    return textwrap.shorten(text, width=max_chars, placeholder="…")


def fetch_likes(client: Client, actor: str, limit: int) -> list:
    posts = []
    cursor = None

    while len(posts) < limit:
        batch_size = min(100, limit - len(posts))
        kwargs = {"actor": actor, "limit": batch_size}
        if cursor:
            kwargs["cursor"] = cursor

        response = client.app.bsky.feed.get_actor_likes(**kwargs)
        feed = response.feed
        if not feed:
            break

        posts.extend(feed)
        cursor = getattr(response, "cursor", None)
        if not cursor:
            break

    return posts[:limit]


def build_rss(handle: str, display_name: str, liked_posts: list) -> str:
    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    channel = ET.SubElement(rss, "channel")

    profile_url = f"https://bsky.app/profile/{handle}"
    ET.SubElement(channel, "title").text = f"{display_name}'s Bluesky Favorites"
    ET.SubElement(channel, "link").text = profile_url
    ET.SubElement(channel, "description").text = (
        f"Posts liked by {handle} on Bluesky"
    )
    ET.SubElement(channel, "language").text = "en"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(
        datetime.now(tz=timezone.utc)
    )
    atom_link = ET.SubElement(channel, "atom:link")
    atom_link.set("href", profile_url)
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    for feed_view in liked_posts:
        post = feed_view.post
        record = post.record
        author = post.author

        text = getattr(record, "text", "") or ""
        created_at_str = getattr(record, "created_at", None) or getattr(
            post, "indexed_at", None
        )

        try:
            created_at = datetime.fromisoformat(
                created_at_str.replace("Z", "+00:00")
            )
            pub_date = format_datetime(created_at)
        except (AttributeError, ValueError):
            pub_date = format_datetime(datetime.now(tz=timezone.utc))

        url = post_url(author.handle, post.uri)
        title = truncate(text) if text else f"Post by @{author.handle}"

        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = url
        ET.SubElement(item, "guid", isPermaLink="true").text = url
        ET.SubElement(item, "pubDate").text = pub_date
        ET.SubElement(item, "author").text = (
            f"{author.handle} ({author.display_name or author.handle})"
        )

        description_parts = [text]
        embed = getattr(post, "embed", None)
        if embed:
            embed_type = type(embed).__name__
            if "Images" in embed_type:
                images = getattr(embed, "images", [])
                for img in images:
                    alt = getattr(img, "alt", "") or ""
                    description_parts.append(f"\n[Image{': ' + alt if alt else ''}]")
            elif "External" in embed_type:
                ext = getattr(embed, "external", None)
                if ext:
                    ext_title = getattr(ext, "title", "") or ""
                    ext_uri = getattr(ext, "uri", "") or ""
                    description_parts.append(f"\n[Link: {ext_title} — {ext_uri}]")
            elif "Record" in embed_type:
                description_parts.append("\n[Quoted post]")

        ET.SubElement(item, "description").text = "".join(description_parts)

    raw = ET.tostring(rss, encoding="unicode")
    pretty = minidom.parseString(raw).toprettyxml(indent="  ")
    # minidom adds an extra XML declaration — keep only one
    lines = pretty.split("\n")
    return "\n".join(lines[1:]) if lines[0].startswith("<?xml") else pretty


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=os.getenv("OUTPUT_FILE", "feed.xml"),
        help="Output file path (default: feed.xml)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.getenv("BSKY_FEED_LIMIT", "100")),
        help="Number of liked posts to fetch (default: 100)",
    )
    args = parser.parse_args()

    handle = os.getenv("BSKY_HANDLE")
    app_password = os.getenv("BSKY_APP_PASSWORD")

    if not handle or not app_password:
        in_ci = os.getenv("CI")
        if in_ci:
            sys.exit(
                "Error: BSKY_HANDLE and BSKY_APP_PASSWORD secrets are not set.\n"
                "Add them at: Settings → Secrets and variables → Actions → New repository secret"
            )
        else:
            sys.exit(
                "Error: BSKY_HANDLE and BSKY_APP_PASSWORD must be set.\n"
                "Copy .env.example to .env and fill in your credentials."
            )

    print(f"Authenticating as {handle}…")
    client = Client()
    profile = client.login(handle, app_password)
    display_name = profile.display_name or handle

    print(f"Fetching up to {args.limit} liked posts…")
    liked = fetch_likes(client, handle, args.limit)
    print(f"Fetched {len(liked)} posts.")

    rss_content = build_rss(handle, display_name, liked)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(rss_content)

    print(f"Feed written to {args.output}")


if __name__ == "__main__":
    main()
