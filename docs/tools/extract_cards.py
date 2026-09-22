"""Extract each individual card from the docs/*.html sprite sheets into its
own PNG file, one per company/train, using each card's data-id attribute for
the filename.

Usage: python3 extract_cards.py
"""
import os

from playwright.sync_api import sync_playwright

DOCS = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

SHEETS = [
    ("train-cards.html", "cards/trains", "train"),
    ("minor-company-cards.html", "cards/minors", None),
    ("private-company-cards.html", "cards/privates", None),
    ("major-company-cards.html", "cards/majors", None),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM)
        page = browser.new_page(viewport={"width": 1400, "height": 1400}, device_scale_factor=2)
        for html_file, out_subdir, prefix in SHEETS:
            out_dir = os.path.join(DOCS, out_subdir)
            os.makedirs(out_dir, exist_ok=True)
            page.goto(f"file://{os.path.join(DOCS, html_file)}")
            page.wait_for_timeout(150)
            cards = page.query_selector_all(".card")
            count = 0
            for card in cards:
                card_id = card.get_attribute("data-id")
                if not card_id:
                    continue
                fname = f"{prefix}_{card_id}.png" if prefix else f"{card_id}.png"
                card.screenshot(path=os.path.join(out_dir, fname))
                count += 1
            print(f"{html_file}: extracted {count} cards -> {out_subdir}/")
        browser.close()


if __name__ == "__main__":
    main()
