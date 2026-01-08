import pandas as pd

REQUIRED_COLS = [
    "keyword", "title", "case_name", "day", "month", "year", "judgment_date", "link"
]

def export_records_to_excel(records: list[dict], out_buffer_or_path):
    """
    Write records to an Excel file with clickable hyperlinks.
    Ensures:
      - Structure identical to CSV (columns in REQUIRED_COLS)
      - Dedup by (keyword, link)
      - Sorted by keyword asc, judgment_date desc
      - Hyperlinks are valid and clickable
    """
    if not records:
        raise ValueError("No records to export")

    # Build DataFrame with consistent columns
    df = pd.DataFrame(records)
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[REQUIRED_COLS]

    # Deduplicate
    df = df.drop_duplicates(subset=["keyword", "link"], keep="first")

    # Normalize judgment_date for sorting
    df["_sort_date"] = pd.to_datetime(df["judgment_date"], errors="coerce")

    # Sort by keyword asc, then judgment_date desc
    df = df.sort_values(
        by=["keyword", "_sort_date"],
        ascending=[True, False],
        na_position="last"
    ).drop(columns=["_sort_date"]).reset_index(drop=True)

    # Drop fully empty rows
    df = df.dropna(how="all").reset_index(drop=True)

    # Write to Excel
    with pd.ExcelWriter(out_buffer_or_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Judgments", index=False)

        workbook = writer.book
        worksheet = writer.sheets["Judgments"]

        # Make link column clickable
        link_col_idx = df.columns.get_loc("link")
        url_format = workbook.add_format({"font_color": "blue", "underline": 1})

        for row_idx in range(len(df)):
            url = df.iloc[row_idx]["link"]
            if pd.notna(url) and str(url).strip():
                worksheet.write_url(row_idx + 1, link_col_idx, str(url), url_format)

        # Optional column widths
        worksheet.set_column(0, 0, 18)  # keyword
        worksheet.set_column(1, 1, 60)  # title
        worksheet.set_column(2, 2, 50)  # case_name
        worksheet.set_column(3, 5, 10)  # day, month, year
        worksheet.set_column(6, 6, 14)  # judgment_date
        worksheet.set_column(7, 7, 42)  # link