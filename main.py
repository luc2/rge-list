from pprint import pprint
import math

import pdfplumber

PDF_FILENAME = "Liste entreprises RGE Muretain Agglo 202602.pdf"


def store_candidate(x: float, score: float, candidates: list[dict[str, any]]) -> None:
    for candidate in candidates:
        if math.isclose(x, candidate["x"]):
            candidate["score"] += score
            break
    else:
        candidates.append(dict(x=x, score=score))


def get_column_index(x: float, column_x: list[float]) -> int:
    for i in range(len(column_x) - 1):
        left = column_x[i]
        right = column_x[i + 1]
        if left <= x < right:
            return i
    return -1


def main() -> None:
    pages = list()

    with pdfplumber.open(PDF_FILENAME) as pdf:
        for page in pdf.pages:
            # print(page.chars)
            chars = sorted(page.chars, key=lambda char: (round(char["top"]), char["x0"]))
            pages.append(chars)

    column_candidates = list()

    # pprint(pages)

    for page in pages:
        # print(page)
        
        # print(len(page.lines))
        # for line in page.lines:
        #     print(line)

        # lines = page.extract_text_lines()
        # pprint(lines)

        # pprint(page.rects)
        # print(type(page.rects))
        # for rect in page.rects:
        #     # print(type(rect))
        #     # pprint(rect)
        #     # x0, top, x1, bottom = crop_bbox
        #     bbox = (rect["x0"], rect["top"], rect["x1"], rect["bottom"])
        #     # print(bbox)
        #     zone = page.within_bbox(bbox)
        #     # print(zone)
        #     lines = zone.extract_text_lines()
        #     for line in lines:
        #         pprint(line)

        last_x = None
        current_line = ""

        for char in page:
            # pprint(char)
            # print(char["text"], end="")

            x0 = char["x0"]

            if last_x and x0 < last_x:
                # print("currentline =", current_line)
                current_line = char["text"]

                candidate_score = last_x - x0
                store_candidate(x0, candidate_score, column_candidates)
            else:
                current_line += char["text"]
                if last_x:
                    candidate_score = x0 - last_x
                    store_candidate(x0, candidate_score, column_candidates)

            last_x = x0
    
    column_candidates.sort(key=lambda candidate: candidate["score"])
    # pprint(column_candidates)

    column_x = [candidate["x"] for candidate in column_candidates[-6:]]
    column_x.sort()
    column_x[3] -= 16
    pprint(column_x)

    for page in pages:
        # print(page)

        last_x = None
        current_line = ""
        current_row = [""] * len(column_x)

        for char in page:
            # pprint(char)
            # print(char["text"], end="")

            x0 = char["x0"]

            if last_x and x0 < last_x:
                # print("currentline =", current_line)
                current_line = char["text"]
                # print(current_row)
                current_row = [""] * len(column_x)
            else:
                current_line += char["text"]

            last_x = x0

            i = get_column_index(x0, column_x)
            current_row[i] += char["text"]
            # print(current_row)

        if current_row != [""] * len(column_x):
            print(current_row)


if __name__ == "__main__":
    main()
