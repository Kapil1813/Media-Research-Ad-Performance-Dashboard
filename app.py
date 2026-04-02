import streamlit as st
import pandas as pd
from openai import OpenAI
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import tempfile

# ------------------------------
# Page Config
# ------------------------------
st.set_page_config(page_title="Media Research Dashboard", layout="wide")
st.title("📊 Media Research & Ad Performance Dashboard")

# ------------------------------
# OpenAI Client
# ------------------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ------------------------------
# Sample Data (Fallback)
# ------------------------------
def sample_linear():
    return pd.DataFrame({
        "Date": pd.date_range(start="2024-01-01", periods=5),
        "Channel": ["NBC", "ABC", "CBS", "FOX", "NBC"],
        "Program": ["Show A", "Show B", "Show C", "Show D", "Show E"],
        "Rating": [2.5, 3.0, 2.8, 3.2, 2.9],
        "Share": [5, 6, 5.5, 6.5, 5.8],
        "Viewers": [2000000, 2500000, 2200000, 2700000, 2300000]
    })

def sample_digital():
    return pd.DataFrame({
        "Date": pd.date_range(start="2024-01-01", periods=5),
        "Platform": ["YouTube", "Hulu", "Roku", "YouTube", "Hulu"],
        "Impressions": [500000, 600000, 550000, 650000, 700000],
        "Clicks": [20000, 25000, 22000, 27000, 30000],
        "Conversions": [2000, 2500, 2300, 2600, 2800],
        "Reach": [300000, 350000, 320000, 360000, 400000]
    })

# ------------------------------
# File Upload
# ------------------------------
st.sidebar.header("📂 Upload Data")

linear_file = st.sidebar.file_uploader("Upload Linear CSV", type=["csv"])
digital_file = st.sidebar.file_uploader("Upload Digital CSV", type=["csv"])

linear_df = pd.read_csv(linear_file, parse_dates=["Date"]) if linear_file else sample_linear()
digital_df = pd.read_csv(digital_file, parse_dates=["Date"]) if digital_file else sample_digital()

# ------------------------------
# Filters
# ------------------------------
platform = st.sidebar.selectbox("Select Platform", ["Linear", "Digital"])

date_range = st.sidebar.date_input(
    "Date Range",
    [linear_df['Date'].min(), linear_df['Date'].max()]
)

# ------------------------------
# Data Filtering
# ------------------------------
if platform == "Linear":
    df = linear_df[
        (linear_df["Date"] >= pd.to_datetime(date_range[0])) &
        (linear_df["Date"] <= pd.to_datetime(date_range[1]))
    ].copy()
else:
    df = digital_df[
        (digital_df["Date"] >= pd.to_datetime(date_range[0])) &
        (digital_df["Date"] <= pd.to_datetime(date_range[1]))
    ].copy()
    df["CTR"] = df["Clicks"] / df["Impressions"]

# ------------------------------
# KPI Section
# ------------------------------
st.header("📈 KPI Metrics")
c1, c2, c3 = st.columns(3)

if platform == "Linear":
    c1.metric("Avg Rating", round(df["Rating"].mean(), 2))
    c2.metric("Total Viewers", int(df["Viewers"].sum()))
    c3.metric("Avg Share", round(df["Share"].mean(), 2))
else:
    c1.metric("Impressions", int(df["Impressions"].sum()))
    c2.metric("Avg CTR", round(df["CTR"].mean(), 4))
    c3.metric("Conversions", int(df["Conversions"].sum()))

# ------------------------------
# Charts
# ------------------------------
st.header("📊 Charts")

if platform == "Linear":
    st.line_chart(df.set_index("Date")["Rating"])
    st.bar_chart(df.groupby("Program")["Viewers"].sum())
else:
    st.line_chart(df.set_index("Date")["CTR"])
    st.bar_chart(df.groupby("Platform")["Impressions"].sum())

# ------------------------------
# AI Insights
# ------------------------------
st.header("💡 AI Insights")

question = st.text_input("Ask a business question")

if st.button("Generate Insights"):
    if not question.strip():
        st.warning("Enter a question")
    else:
        with st.spinner("Analyzing..."):
            try:
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a media analytics expert."},
                        {"role": "user", "content": f"Data: {df.head(20).to_dict(orient='records')} Question: {question}"}
                    ]
                )
                st.success(res.choices[0].message.content)
            except Exception as e:
                st.error(e)

# ------------------------------
# BA Assistant (User Input Driven)
# ------------------------------
st.header("📝 BA Assistant - User Stories Generator")

requirement = st.text_area("Enter Business Requirement")

generated_text = ""

if st.button("Generate User Stories"):
    if not requirement.strip():
        st.warning("Enter requirement")
    else:
        with st.spinner("Generating..."):
            try:
                prompt = f"""
                You are a Senior Business Analyst.

                Requirement:
                {requirement}

                Generate EXACTLY 3 user stories.

                Format:

                User Story 1:
                As a <role>, I want <goal>, so that <value>

                Acceptance Criteria:
                - bullet
                - bullet

                Data Requirements:
                - fields

                Workflow:
                - steps

                Repeat for 3.
                """

                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a Business Analyst expert."},
                        {"role": "user", "content": prompt}
                    ]
                )

                generated_text = res.choices[0].message.content

                if generated_text:
                    st.success("Generated!")
                    st.write(generated_text)
                else:
                    st.warning("Empty output")

            except Exception as e:
                st.error(e)

# ------------------------------
# PDF Download
# ------------------------------
if generated_text:
    if st.button("Download BRD PDF"):
        try:
            temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

            doc = SimpleDocTemplate(temp.name)
            styles = getSampleStyleSheet()

            content = []
            content.append(Paragraph("Business Requirements Document", styles["Title"]))
            content.append(Spacer(1, 12))

            content.append(Paragraph(f"<b>Requirement:</b> {requirement}", styles["Normal"]))
            content.append(Spacer(1, 12))

            for line in generated_text.split("\n"):
                content.append(Paragraph(line, styles["Normal"]))
                content.append(Spacer(1, 6))

            doc.build(content)

            with open(temp.name, "rb") as f:
                st.download_button("📄 Download PDF", f, "BRD.pdf")

        except Exception as e:
            st.error(e)