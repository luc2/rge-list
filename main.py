import json
import os
import re
import time
import unicodedata
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

COMPANIES_FILENAME = "entreprises_rge.json"
OUTPUT_FILENAME = "entreprises_rge_details.json"

GOOGLE_API_KEY = os.environ["GOOGLE_API_KEY"]
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
SEARCH_FIELDS = ",".join([
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.websiteUri",
    "places.rating",
    "places.userRatingCount",
    "places.reviews",
    "places.googleMapsUri",
    "places.types",
    "places.businessStatus",
])


def load_companies() -> list[dict]:
    with open(COMPANIES_FILENAME, "r", encoding="utf-8") as f:
        return json.load(f)


def save_companies(companies: list[dict]) -> None:
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        json.dump(companies, f, ensure_ascii=False, indent=4)


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_phone(phone: str) -> str:
    return re.sub(r"[^\d]", "", phone)


def score_place(place: dict, company: dict) -> int:
    score = 0

    g_name = normalize(place.get("displayName", {}).get("text", ""))
    c_name = normalize(company["name"])
    if g_name == c_name:
        score += 2
    elif c_name in g_name or g_name in c_name:
        score += 1

    g_addr = normalize(place.get("formattedAddress", ""))
    c_addr = normalize(company["address"])
    if c_addr and c_addr in g_addr:
        score += 1

    c_commune = normalize(company["commune"])
    if c_commune in g_addr:
        score += 1

    g_phone = normalize_phone(place.get("nationalPhoneNumber", ""))
    c_phone = normalize_phone(company.get("telephone", ""))
    if c_phone and g_phone and (c_phone.endswith(g_phone[-8:]) or g_phone.endswith(c_phone[-8:])):
        score += 1

    return score


def build_query(company: dict) -> str:
    return f"{company['name']} {company['commune']}"


def search_places(client: httpx.Client, query: str) -> tuple[list[dict], int]:
    resp = client.post(
        PLACES_SEARCH_URL,
        headers={
            "X-Goog-Api-Key": GOOGLE_API_KEY,
            "X-Goog-FieldMask": SEARCH_FIELDS,
            "Content-Type": "application/json",
        },
        json={
            "textQuery": query,
            "languageCode": "fr",
            "regionCode": "fr",
        },
    )
    resp.raise_for_status()
    places = resp.json().get("places", [])
    return places, len(places)


def extract_google_info(place: dict, total_results: int) -> dict:
    display_name = place.get("displayName", {})
    return {
        "total_results": total_results,
        "place_id": place.get("id"),
        "name": display_name.get("text"),
        "address": place.get("formattedAddress"),
        "phone": place.get("nationalPhoneNumber"),
        "website": place.get("websiteUri"),
        "google_maps_url": place.get("googleMapsUri"),
        "rating": place.get("rating"),
        "total_reviews": place.get("userRatingCount"),
        "types": place.get("types", []),
        "business_status": place.get("businessStatus"),
        "reviews": [
            {
                "author": r.get("authorAttribution", {}).get("displayName"),
                "rating": r.get("rating"),
                "text": r.get("text", {}).get("text", ""),
                "relative_time": r.get("relativePublishTimeDescription"),
                "visit_date": r.get("visitDate"),
            }
            for r in (place.get("reviews") or [])[:5]
        ],
    }


def enrich_company(client: httpx.Client, company: dict, index: int, total: int) -> dict:
    query = build_query(company)
    print(f"[{index + 1}/{total}] {company['name']} -> '{query}'")

    places, total_results = search_places(client, query)
    if not places:
        print(f"  Aucun résultat trouvé")
        return {**company, "google": None, "total_results": 0}

    scored = [(score_place(p, company), p) for p in places]
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_place = scored[0]

    google_info = extract_google_info(best_place, total_results)
    google_info["match_score"] = best_score
    print(f"  -> score={best_score}/{len(scored)} résultats, note={google_info.get('rating')}, avis={google_info.get('total_reviews', 0)}")
    return {**company, "google": google_info}


def main() -> None:
    companies = load_companies()
    total = len(companies)

    existing: list[dict] = []
    if Path(OUTPUT_FILENAME).exists():
        with open(OUTPUT_FILENAME, "r", encoding="utf-8") as f:
            existing = json.load(f)

    done_names = {c["name"] for c in existing if c.get("google") is not None}
    results = existing[:]

    print(f"{total} entreprises à traiter, {len(done_names)} déjà traitées\n")

    with httpx.Client(timeout=30.0) as client:
        for i, company in enumerate(companies):
            if company["name"] in done_names:
                print(f"[{i + 1}/{total}] {company['name']} -> déjà traité, skip")
                continue

            enriched = enrich_company(client, company, i, total)
            results.append(enriched)
            time.sleep(0.05)

            if (i + 1) % 10 == 0:
                save_companies(results)
                print(f"  -- sauvegarde intermédiaire --\n")
            else:
                print()

    save_companies(results)
    print(f"\nTerminé ! {total} entreprises traitées, résultats dans {OUTPUT_FILENAME}")


if __name__ == "__main__":
    main()
