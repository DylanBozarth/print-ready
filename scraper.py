import sys
import os
import io
import argparse
import requests
from bs4 import BeautifulSoup
from PIL import Image as PilImage
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

HEADERS = {"User-Agent": "Mozilla/5.0"}
PAGE_CONTENT_WIDTH = letter[0] - 2 * inch  # 6.5 inches
PX_TO_POINTS = 72 / 96  # 96dpi screen pixels to PDF points


def get_title(soup) -> str:
    tag = soup.find("title")
    title = tag.get_text().strip() if tag else "scraped_output"
    return "".join(c if c.isalnum() or c in " -_" else " " for c in title).strip()


def fetch_image(src: str, base_url: str) -> io.BytesIO | None:
    if src.startswith("//"):
        src = "https:" + src
    elif src.startswith("/"):
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        src = f"{parsed.scheme}://{parsed.netloc}{src}"
    elif not src.startswith("http"):
        return None
    try:
        resp = requests.get(src, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        img = PilImage.open(io.BytesIO(resp.content)).convert("L")  # greyscale
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception:
        return None


def scrape_tags(url: str, include_images: bool) -> tuple[str, list[tuple[str, str | io.BytesIO]]]:
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup.find_all(["nav", "header", "footer", "tbody"]):
        tag.decompose()

    SKIP_SECTIONS = {
        "references", "bibliography", "ancestry", "see also",
        "external links", "notes", "further reading", "footnotes",
        "sources", "citations", "citation", "source",
    }

    tags = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "tr", "img"])
    results = []
    skip = False
    for tag in tags:
        if tag.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            skip = tag.get_text(separator=" ").strip().lower() in SKIP_SECTIONS

        if skip:
            continue

        if tag.name == "img":
            if include_images:
                src = tag.get("src", "")
                buf = fetch_image(src, url)
                if buf:
                    html_w = tag.get("width")
                    html_h = tag.get("height")
                    results.append(("img", (buf, html_w, html_h)))
            continue

        if tag.name == "tr":
            cells = [td.get_text(separator=" ").strip() for td in tag.find_all(["td", "th"])]
            row_text = " | ".join(c for c in cells if c)
            if row_text and "©" not in row_text:
                results.append(("tr", row_text))
            continue

        for a in tag.find_all("a"):
            a.unwrap()
        for span in tag.find_all("span"):
            span.decompose()
        text = tag.get_text(separator=" ").strip()
        if text and "©" not in text and "&copy;" not in text:
            results.append((tag.name, text))

    return get_title(soup), results


def save_pdf(items: list, output_path: str) -> None:
    styles = getSampleStyleSheet()
    heading_styles = {
        "h1": styles["h1"],
        "h2": styles["h2"],
        "h3": styles["h3"],
        "h4": styles["h4"],
        "h5": styles["h5"],
        "h6": styles["h6"],
    }

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    story = []
    for tag_name, content in items:
        if tag_name == "img":
            try:
                buf, html_w, html_h = content
                img = PilImage.open(buf)
                nat_w, nat_h = img.size

                # prefer HTML-specified dimensions, fall back to natural pixel size
                try:
                    display_w = float(html_w) * PX_TO_POINTS if html_w else nat_w * PX_TO_POINTS
                    display_h = float(html_h) * PX_TO_POINTS if html_h else nat_h * PX_TO_POINTS
                except (ValueError, TypeError):
                    display_w = nat_w * PX_TO_POINTS
                    display_h = nat_h * PX_TO_POINTS

                # scale down only if wider than the page content area
                if display_w > PAGE_CONTENT_WIDTH:
                    scale = PAGE_CONTENT_WIDTH / display_w
                    display_w = PAGE_CONTENT_WIDTH
                    display_h *= scale

                buf.seek(0)
                story.append(Image(buf, width=display_w, height=display_h))
                story.append(Spacer(1, 6))
            except Exception:
                pass
            continue

        style = heading_styles.get(tag_name, styles["Code"] if tag_name == "tr" else styles["Normal"])
        story.append(Paragraph(content, style))
        story.append(Spacer(1, 6))

    doc.build(story)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape a webpage to PDF.")
    parser.add_argument("url", help="URL to scrape")
    parser.add_argument("--images", action="store_true", help="Include images (converted to greyscale)")
    args = parser.parse_args()

    title, items = scrape_tags(args.url, include_images=args.images)

    for tag_name, content in items:
        if tag_name != "img":
            print(content)

    desktop = os.path.join(os.path.expanduser("~"), "Desktop", f"{title}.pdf") #save it to desktop
    save_pdf(items, desktop)
    print(f"\nPDF saved to: {desktop}")
