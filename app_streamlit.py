import io
import os, sys
import time
import datetime
import subprocess, json
import streamlit as st
from db import init_db, insert_records
from export import export_records_to_excel
from mailer import send_email_with_attachment
import requests

DB_PATH = "judgments.db"

st.set_page_config(page_title="Judgement Scraper", layout="wide")
st.title("Supreme Court judgments scraper")

# Initialize DB
init_db(DB_PATH)

# Sidebar: settings
st.sidebar.header("Settings")
max_links = st.sidebar.number_input("Top links per keyword", min_value=1, max_value=50, value=10, step=1)
headless = st.sidebar.checkbox("Run browser headless", value=True)


def run_scraper_subprocess(keyword, max_links=10, headless=True):
    result = subprocess.run(
        [sys.executable, "scraper.py", keyword, str(max_links), str(int(headless))],
        capture_output=True, text=True
    )
    try:
        return json.loads(result.stdout)
    except Exception as e:
        print("JSON decode error:", e)
        return []


# Ensure session state for scraped records
if "all_records" not in st.session_state:
    st.session_state["all_records"] = []

st.header("1. Upload keywords file and scrape")
uploaded_file = st.file_uploader("Upload a .txt file with one keyword per line", type=["txt"])

if uploaded_file:
    content = uploaded_file.read().decode("utf-8")
    keywords = [line.strip() for line in content.splitlines() if line.strip()]
    st.write(f"Loaded {len(keywords)} keyword(s).")

    if st.button("Scrape top links for keywords"):
        progress = st.progress(0)
        status = st.empty()
        all_records = []
        for i, kw in enumerate(keywords, start=1):
            status.write(f"Scraping: {kw}")
            try:
                records = run_scraper_subprocess(kw, max_links=max_links, headless=headless)
                insert_records(DB_PATH, records)
                all_records.extend(records)
                st.success(f"{kw}: captured {len(records)} record(s).")
            except Exception as e:
                st.error(f"Error scraping '{kw}': {e}")
            progress.progress(i / len(keywords))
            time.sleep(0.1)

        st.write("Done.")
        if all_records:
            st.session_state["all_records"] = all_records  # persist results
            st.dataframe(all_records)

            # CSV export
            csv_buffer = io.StringIO()
            import csv
            writer = csv.DictWriter(csv_buffer, fieldnames=all_records[0].keys())
            writer.writeheader()
            writer.writerows(all_records)
            st.download_button(
                label="Download CSV",
                data=csv_buffer.getvalue(),
                file_name=f"judgments_{datetime.date.today().isoformat()}.csv",
                mime="text/csv",
            )

            # Excel export (scrape results only)
            excel_buffer = io.BytesIO()
            export_records_to_excel(all_records, excel_buffer)
            excel_buffer.seek(0)
            st.download_button(
                label="Download Excel",
                data=excel_buffer,
                file_name=f"judgments_{datetime.date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
# send SMS to mobile.
def send_notification_sms(to_number, message, api_key):
    url = "https://api.smsmobileapi.com/sendsms/"
    payload = {
        "recipients": to_number,
        "message": message,
        "apikey": api_key
    }
    resp = requests.post(url, data=payload)
    if resp.status_code == 200:
        print("SMS notification sent")
    else:
        print("SMS failed:", resp.text)



st.header("3. Mail me the judgments")
with st.form("email_form"):
    to_email = st.text_input("Recipient email")
    smtp_host = st.text_input("SMTP host", value="smtp.gmail.com")
    smtp_port = st.number_input("SMTP port", value=587)
    smtp_user = st.text_input("SMTP username (your Gmail address)", value="sridharnarasimhan.crystal@gmail.com")
    smtp_pass = st.text_input("SMTP password (your 16-digit App Password)", type="password")
    submitted = st.form_submit_button("Send email")

    if submitted:
        if not st.session_state["all_records"]:
            st.warning("No judgments available. Please run the scraper first.")
        else:
            buf = io.BytesIO()
            export_records_to_excel(st.session_state["all_records"], buf)  # use same records
            buf.seek(0)
            try:
                send_email_with_attachment(
                    smtp_host=smtp_host,
                    smtp_port=int(smtp_port),
                    smtp_user=smtp_user,
                    smtp_pass=smtp_pass,
                    to_email=to_email,
                    subject="Scraped judgments",
                    body="Please find attached the judgments you scraped.",
                    attachment_bytes=buf.getvalue(),
                    attachment_filename=f"judgments_{datetime.date.today().isoformat()}.xlsx",
                )
                send_notification_sms("+919980033399", "Hi Vishwesh, Check your judgments mail", "39a6ec09adf3e9304cad416e6bfc56eca324fadd0e36de9d")
                st.success("Email & SMS sent.")
            except Exception as e:
                st.error(f"Failed to send email: {e}")