import pdfplumber

with pdfplumber.open("report.pdf") as pdf:
    num_pages = len(pdf.pages)
    print(f"Total pages: {num_pages}")

    all_text = ""

    for page_number, page in enumerate(pdf.pages):
        page_text = page.extract_text()

        if page_text:
            all_text += page_text + "\n"
        else:
            print(f"Page {page_number + 1}: no text extracted (possibly scanned or empty).")

    print(f"\nTotal characters extracted: {len(all_text)}")

with open("output_full_text.txt", "w", encoding="utf-8") as file:
    file.write(all_text)

print("Full text saved to output_full_text.txt")

import csv

with pdfplumber.open("report.pdf") as pdf:
    target_page_index = None

    for page_number, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text and "CONSOLIDATED STATEMENTS OF OPERATIONS" in text.upper():
            target_page_index = page_number
            print(f"Found target page at index {page_number} (printed page ~{page_number + 1})")
            break

    if target_page_index is not None:
        target_page = pdf.pages[target_page_index]
        text_check = target_page.extract_text()
        print("\n=== VERIFY: first 300 characters of found page ===")
        print(text_check[:300])

        table_settings = {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
        }

        tables = target_page.extract_tables(table_settings=table_settings)
        print(f"\nNumber of tables found: {len(tables)}")

        if tables:
            income_statement = tables[0]
            with open("output/income_statement.csv", "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerows(income_statement)
            print("Table saved to output/income_statement.csv")
        else:
            print("No tables detected on this page.")
    else:
        print("Could not find the target page automatically.")