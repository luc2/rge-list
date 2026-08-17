import json
from pathlib import Path
from pprint import pprint

from dotenv import load_dotenv

load_dotenv()

COMPANIES_FILENAME = "entreprises_rge.json"


def load_companies() -> list[dict]:
    companies_path = Path(COMPANIES_FILENAME)

    with companies_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> None:
    companies = load_companies()
    pprint(companies)


if __name__ == "__main__":
    main()
