import re
from collections import defaultdict

import pdfplumber

PDF_FILENAME = "Liste entreprises RGE Muretain Agglo 202602.pdf"
COLUMN_EDGES = [17, 144, 286, 406, 465, 689, 823]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def gather_rows_from_page(page):
    rows = defaultdict(lambda: [""] * (len(COLUMN_EDGES) - 1))
    y_keys = []

    for char in page.chars:
        top = round(char["top"], 1)
        key = None
        for existing in y_keys:
            if abs(existing - top) <= 2:
                key = existing
                break
        if key is None:
            key = top
            y_keys.append(key)

        col = None
        for index in range(len(COLUMN_EDGES) - 1):
            if COLUMN_EDGES[index] - 1 <= char["x0"] < COLUMN_EDGES[index + 1] - 1:
                col = index
                break
        if col is None:
            continue

        rows[key][col] += char["text"]

    return [rows[key] for key in sorted(y_keys)]


def parse_rows(raw_rows):
    entries = []
    in_group_section = False
    
    # Group rows by company: each company starts with a name in col 0
    company_groups = []
    current_group = []

    for raw_row in raw_rows:
        row = [normalize_text(cell) for cell in raw_row]
        
        # Skip headers, blank rows, and page numbers
        if row[0].lower().startswith("nom de l'entreprise") or all(not cell for cell in row) or (not row[0] and not row[1] and not row[2] and not row[3] and not row[4] and row[5].isdigit()):
            continue
        
        # Check for groupement header
        if any("groupement" in cell.lower() or "regroupement" in cell.lower() for cell in row):
            in_group_section = True
            continue
        
        # Start new group if we have a name in col 0
        if row[0]:
            if current_group:
                company_groups.append((current_group, in_group_section))
            current_group = [row]
        else:
            # Continuation row: add to current group (or start one if none exists)
            if current_group:
                current_group.append(row)
            else:
                # Orphan continuation - shouldn't happen but group it anyway
                current_group = [row]
    
    if current_group:
        company_groups.append((current_group, in_group_section))
    
    # Merge each group into a single entry
    for group, is_group in company_groups:
        if not group:
            continue
        
        # Start with first row
        entry = {
            "name": group[0][0],
            "address": group[0][1],
            "commune": group[0][2],
            "telephone": group[0][3],
            "sector": group[0][4],
            "email": group[0][5],
            "is_groupement": is_group,
        }
        
        # Merge continuation rows
        for continuation in group[1:]:
            # Merge address (col 1)
            if continuation[1]:
                entry["address"] = normalize_text(entry["address"] + " " + continuation[1])
            # Merge telephone (col 3) - with separator if already has value
            if continuation[3]:
                if entry["telephone"]:
                    entry["telephone"] = normalize_text(entry["telephone"] + " / " + continuation[3])
                else:
                    entry["telephone"] = continuation[3]
            # Merge sector (col 4)
            if continuation[4]:
                entry["sector"] = normalize_text((entry["sector"] or "") + " " + continuation[4])
        
        # Only add if has a name
        if entry["name"]:
            entries.append(entry)
    
    return entries


def extract_all_entries(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        all_entries = []
        for page_number, page in enumerate(pdf.pages, start=1):
            raw_rows = gather_rows_from_page(page)
            entries = parse_rows(raw_rows)
            for entry in entries:
                entry["page"] = page_number
            all_entries.extend(entries)
    return all_entries


def main():
    entries = extract_all_entries(PDF_FILENAME)
    print(f"Total entreprises/regroupements extraits: {len(entries)}\n")
    for idx, entry in enumerate(entries, 1):
        print(f"{idx}. {entry['name']} | {entry['address']} | {entry['commune']} | {entry['telephone']} | {entry['sector']} | {entry['email']} | regroupement={entry['is_groupement']} | page={entry['page']}")


if __name__ == "__main__":
    main()
