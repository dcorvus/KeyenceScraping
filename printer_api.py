# printer_api.py

from datetime import datetime, timezone
from typing import Any

import json
import threading

from fastapi import FastAPI, Response
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


WEB_TARGETS = [
    {
        "url": "http://192.168.141.88/html/home.html?lang=en&version=02.03.04",
        "username": "user",
        "password": "10399",
    },
    {
        "url": "http://192.168.140.89/html/home.html?lang=en&version=02.08.02",
        "username": "user",
        "password": "10399",
    },
    {
        "url": "http://192.168.142.207/html/home.html?lang=en&version=02.06.01",
        "username": "user",
        "password": "10399",
    },
]


SCRAPE_JS = """
(cards) => {
    function cleanText(value) {
        return (value || "").replace(/\\s+/g, " ").trim();
    }

    function isBadValue(value) {
        if (value === null || value === undefined) return true;

        const text = cleanText(String(value));

        if (!text) return true;

        // Reject Vue / template placeholder strings
        if (text.includes("{{") || text.includes("}}")) return true;

        const lowered = text.toLowerCase();

        if (
            lowered === "null" ||
            lowered === "undefined" ||
            lowered === "nan"
        ) {
            return true;
        }

        return false;
    }

    function isVisible(el) {
        if (!el) return false;

        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            style.opacity !== "0" &&
            rect.width > 0 &&
            rect.height > 0
        );
    }

    function readRawValue(card, dataAuto) {
        const el = card.querySelector(`[data-auto="${dataAuto}"]`);
        if (!el) return null;

        const value = cleanText(
            el.innerText ||
            el.textContent ||
            el.value ||
            el.getAttribute("value") ||
            el.getAttribute("title") ||
            ""
        );

        return isBadValue(value) ? null : value;
    }

    function removePercent(value) {
        if (isBadValue(value)) return null;

        return cleanText(
            String(value)
                .replace(/%/g, "")
        );
    }

    function removeHoursLeft(value) {
        if (isBadValue(value)) return null;

        return cleanText(
            String(value)
                .replace(/h\\s*left/gi, "")
                .replace(/hours\\s*left/gi, "")
                .replace(/hr\\s*left/gi, "")
        );
    }

    function readParagraphUnderName(card, nameEl) {
        if (!nameEl) return null;

        let node = nameEl.nextElementSibling;

        while (node) {
            if (node.tagName && node.tagName.toLowerCase() === "p") {
                const value = cleanText(node.innerText || node.textContent);
                return isBadValue(value) ? null : value;
            }

            const pInside = node.querySelector && node.querySelector("p");
            if (pInside) {
                const value = cleanText(pInside.innerText || pInside.textContent);
                return isBadValue(value) ? null : value;
            }

            node = node.nextElementSibling;
        }

        const walker = document.createTreeWalker(
            card,
            NodeFilter.SHOW_ELEMENT
        );

        walker.currentNode = nameEl;

        while (walker.nextNode()) {
            const current = walker.currentNode;

            if (
                current.tagName &&
                current.tagName.toLowerCase() === "p"
            ) {
                const value = cleanText(current.innerText || current.textContent);
                return isBadValue(value) ? null : value;
            }
        }

        const fallbackP = card.querySelector("p");

        if (fallbackP) {
            const value = cleanText(fallbackP.innerText || fallbackP.textContent);
            return isBadValue(value) ? null : value;
        }

        return null;
    }

    const results = [];

    for (const card of cards) {
        if (!isVisible(card)) {
            continue;
        }

        const nameEl = card.querySelector(`[data-auto="name.name"]`);

        if (!nameEl) {
            continue;
        }

        if (!isVisible(nameEl)) {
            continue;
        }

        const name = readRawValue(card, "name.name");

        // If name.name is missing, blank, or still a template variable,
        // do NOT push this card into the final array.
        if (isBadValue(name)) {
            continue;
        }

        const inkLevelRaw = readRawValue(card, "level.ink");
        const solventLevelRaw = readRawValue(card, "level.solvent");
        const pumpHoursRaw = readRawValue(card, "operation_time.pump");
        const filterAHoursRaw = readRawValue(card, "operation_time.filter_a");
        const filterBHoursRaw = readRawValue(card, "operation_time.filter_b");

        results.push({
            Name: name,
            IP: readParagraphUnderName(card, nameEl),
            InkLevel: removePercent(inkLevelRaw),
            SolventLevel: removePercent(solventLevelRaw),
            PumpHoursLeft: removeHoursLeft(pumpHoursRaw),
            FilterAHoursRemaining: removeHoursLeft(filterAHoursRaw),
            FilterBHoursRemaining: removeHoursLeft(filterBHoursRaw)
        });
    }

    return results;
}
"""


app = FastAPI(title="Printer Scrape API")


cache_lock = threading.Lock()

printer_cache: dict[str, Any] = {
    "ScrapedAt": None,
    "Count": 0,
    "Data": [],
    "Errors": [],
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def scrape_one_url(page, web_url: str) -> tuple[list[dict[str, Any]], str | None]:
    try:
        page.goto(web_url, wait_until="networkidle", timeout=45000)
        page.wait_for_selector("div.card-wrap", timeout=30000)

        page.wait_for_function(
            """
            () => {
                const cards = Array.from(document.querySelectorAll("div.card-wrap"));

                return cards.some(card => {
                    const el = card.querySelector('[data-auto="name.name"]');
                    if (!el) return false;

                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();

                    const visible =
                        style.display !== "none" &&
                        style.visibility !== "hidden" &&
                        style.opacity !== "0" &&
                        rect.width > 0 &&
                        rect.height > 0;

                    const text = (el.innerText || el.textContent || "").trim();

                    return (
                        visible &&
                        text &&
                        !text.includes("{{") &&
                        !text.includes("}}")
                    );
                });
            }
            """,
            timeout=30000,
        )

        data = page.eval_on_selector_all("div.card-wrap", SCRAPE_JS)
        return data, None

    except PlaywrightTimeoutError:
        return [], "Timed out or no hydrated card data found for one device page."

    except Exception as exc:
        return [], f"Failed scraping one device page: {exc}"


def scrape_printer_data() -> dict[str, Any]:
    scraped_at = utc_now_iso()
    all_results: list[dict[str, Any]] = []
    errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for target in WEB_TARGETS:
            web_url = target["url"]
            username = target["username"]
            password = target["password"]

            context = browser.new_context(
                http_credentials={
                    "username": username,
                    "password": password,
                }
            )

            page = context.new_page()

            page_results, error = scrape_one_url(page, web_url)

            if error:
                errors.append(error)
            else:
                for item in page_results:
                    item["ScrapedAt"] = scraped_at
                    all_results.append(item)

            context.close()

        browser.close()

    return {
        "ScrapedAt": scraped_at,
        "Count": len(all_results),
        "Data": all_results,
        "Errors": errors,
    }


def refresh_cache() -> dict[str, Any]:
    global printer_cache

    fresh_data = scrape_printer_data()

    with cache_lock:
        printer_cache = fresh_data

    return fresh_data


@app.get("/")
def root():
    return {
        "Status": "OK",
        "Service": "Printer Scrape API",
        "Endpoints": [
            "/api/health",
            "/api/printer-data",
            "/api/printer-data/refresh",
            "/api/printer-data.js",
        ],
    }


@app.get("/api/health")
def health():
    return {
        "Status": "OK",
        "CachedCount": printer_cache["Count"],
        "LastScrapedAt": printer_cache["ScrapedAt"],
        "ErrorCount": len(printer_cache["Errors"]),
    }


@app.get("/api/printer-data")
def get_printer_data():
    return printer_cache


@app.get("/api/printer-data/refresh")
def refresh_printer_data():
    return refresh_cache()


@app.get("/api/printer-data.js")
def get_printer_data_js():
    js_array = "const printerData = " + json.dumps(
        printer_cache["Data"],
        indent=4,
    ) + ";"

    return Response(
        content=js_array,
        media_type="application/javascript",
    )


@app.on_event("startup")
def startup_scrape():
    try:
        refresh_cache()
    except Exception as exc:
        with cache_lock:
            printer_cache["Errors"].append(f"Startup scrape failed: {exc}")