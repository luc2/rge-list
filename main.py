import json
import os
import time
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


def build_query(company: dict) -> str:
    return f"{company['name']} {company['commune']}"


def search_place(client: httpx.Client, query: str) -> dict | None:
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
    return places[0] if places else None


def extract_google_info(place: dict) -> dict:
    display_name = place.get("displayName", {})
    return {
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

    place = search_place(client, query)
    if not place:
        print(f"  Aucun résultat trouvé")
        return {**company, "google": None}

    google_info = extract_google_info(place)
    print(f"  -> note={google_info.get('rating')}, avis={google_info.get('total_reviews', 0)}")
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
