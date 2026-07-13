import sys
import os
import requests
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


def get_title(soup) -> str:
    tag = soup.find("title")
    title = tag.get_text().strip() if tag else "scraped_output"
    return "".join(c if c.isalnum() or c in " -_" else " " for c in title).strip()


def scrape_tags(url: str) -> tuple[str, list[tuple[str, str]]]:
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup.find_all(["nav", "header", "footer"]):
        tag.decompose()

    SKIP_SECTIONS = {
        "references", "bibliography", "ancestry", "see also",
        "external links", "notes", "further reading", "footnotes",
    }

    tags = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "tr"])
    results = []
    skip = False
    for tag in tags:
        if tag.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            skip = tag.get_text(separator=" ").strip().lower() in SKIP_SECTIONS

        if skip:
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


def save_pdf(items: list[tuple[str, str]], output_path: str) -> None:
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
    for tag_name, text in items:
        style = heading_styles.get(tag_name, styles["Code"] if tag_name == "tr" else styles["Normal"])
        story.append(Paragraph(text, style))
        story.append(Spacer(1, 6))

    doc.build(story)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scraper.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    title, items = scrape_tags(url)

    for _, text in items:
        print(text)

    desktop = os.path.join(os.path.expanduser("~"), "Desktop", f"{title}.pdf") #save it to desktop
    save_pdf(items, desktop)
    print(f"\nPDF saved to: {desktop}")
