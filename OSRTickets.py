import streamlit as st
st.set_page_config(page_title="Support Tickets", page_icon="🎫", layout="wide")
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import matplotlib.pyplot as plt
from googleapiclient.http import MediaFileUpload
import seaborn as sns
import datetime
import pandas as pd
import os
import io
import time

# Access the credentials stored in Streamlit secrets
google_secrets = st.secrets["google_service_account"]["service_account_json"]

# Parse the JSON string from secrets into a Python dictionary
service_account_info = json.loads(google_secrets)

# Construct the credentials using the service account info
credentials = Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/drive.file"]
)

# Build the Google Drive API client
drive_service = build('drive', 'v3', credentials=credentials)

# Define function to upload data to Google Drive
def upload_file(file_path, file_name):
    results = drive_service.files().list(
        q=f"name='{file_name}'", fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if items:
        file_id = items[0]['id']
        drive_service.files().delete(fileId=file_id).execute()
    
    media = MediaFileUpload(file_path, mimetype='application/vnd.ms-excel')
    file = drive_service.files().create(
        media_body=media,
        body={'name': file_name}
    ).execute()
    return file.get('id')

def save_to_drive(df, file_name):
    file_path = f"/tmp/{file_name}"
    df.to_csv(file_path, index=False)
    upload_file(file_path, file_name)

def load_data():
    file_name = 'StatisticalAnalysisTickets.csv'
    query = f"name='{file_name}'"
    result = drive_service.files().list(q=query).execute()
    if result['files']:
        file_id = result['files'][0]['id']
        request = drive_service.files().get_media(fileId=file_id)
        data = request.execute()
        return pd.read_csv(io.BytesIO(data))
    return pd.DataFrame(columns=["ID", "Request Type", "Email", "Department", "Status", "Priority", "Date Submitted", "Summary"])

# Initialize or load data into session state
if "df" not in st.session_state:
    st.session_state.df = load_data()

# Reset functionality
def reset_data(password):
    correct_password = "reset123"  # Replace with a secure password
    if password == correct_password:
        st.session_state.df = pd.DataFrame(columns=["ID", "Request Type", "Email", "Department", "Status", "Priority", "Date Submitted", "Summary"])
        save_to_drive(st.session_state.df, 'StatisticalAnalysisTickets.csv')
        return True
    return False

# Streamlit page configuration
st.title("Office of Surgical Research")
st.header("Statistical Support")

# Ticket Form
st.subheader("Submit a Support Ticket")
departments = [
    "Dentistry and Oral Health", "Ophthalmology", "Orthopaedic", "Pediatric Surgery", 
    "Podiatry", "Transplant Surgery", "Vascular Surgery", "General Surgery",
    "Oral and Maxillofacial", "Otolaryngology", "Plastic Surgery", 
    "Thoracic Surgery", "Urology"
]

# Form for ticket creation
with st.form("add_ticket_form"):
    name = st.text_area("Name", placeholder="Please enter your full name here")
    request_type = st.selectbox("Request Type", ["New", "Follow-up"])
    department = st.selectbox("Department", departments)
    email = st.text_area("Email Address", placeholder="Enter your email address here...")
    issue = st.text_area("Description of the Issue", placeholder="Briefly describe the work or issue you're submitting.")
    priority = st.selectbox("Priority Level", ["High", "Medium", "Low"])
    date_submitted = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = issue[:5000]  # Create a brief summary (first 5000 characters)

    submitted = st.form_submit_button("Submit")
    if submitted:
        ticket_id = f"T{len(st.session_state.df) + 1}"
        new_ticket = {
            "ID": ticket_id,
            "name": name,
            "Request Type": request_type,
            "Email": email,
            "Department": department,
            "Status": "Open",
            "Priority": priority,
            "Date Submitted": date_submitted,
            "Summary": summary,
        }
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_ticket])], ignore_index=True)
        save_to_drive(st.session_state.df, 'StatisticalAnalysisTickets.csv')
        st.success(f"Ticket {ticket_id} has been submitted successfully!")

# Display Ticket Table
st.subheader("Submitted Tickets")

# Editable table with status selection for each ticket
status_options = ["Open", "In Progress", "Completed"]
for idx, row in st.session_state.df.iterrows():
    col1, col2, col3, col4 = st.columns([1, 2, 2, 2])

    with col1:
        st.write(f"Ticket ID: {row['ID']}")
    
    with col2:
        st.write(f"Name: {row['name']}")

    with col3:
        status = st.selectbox(
            label="Status", 
            options=status_options, 
            index=status_options.index(row['Status']),
            key=f"status_{row['ID']}"
        )
    
    with col4:
        if st.button(f"Update Status for Ticket {row['ID']}", key=f"update_{row['ID']}"):
            st.session_state.df.at[idx, 'Status'] = status
            save_to_drive(st.session_state.df, 'StatisticalAnalysisTickets.csv')
            st.success(f"Status for Ticket {row['ID']} has been updated to {status}")

# Insights section
if not st.session_state.df.empty:
    df = st.session_state.df
    priority_counts = df["Priority"].value_counts()
    status_counts = df["Status"].value_counts()
    department_counts = df["Department"].value_counts()

    st.header("Ticket Insights")
    col1, col2, col3 = st.columns(3)

    def generate_color_palette(n):
        return sns.color_palette("husl", n)

    with col1:
        st.subheader("Tickets by Priority")
        fig, ax = plt.subplots(figsize=(4, 3))
        priority_counts.plot(kind="bar", color=generate_color_palette(len(priority_counts)), ax=ax)
        ax.set_title("Priority Distribution")
        ax.set_ylabel("Count")
        st.pyplot(fig)

    with col2:
        st.subheader("Tickets by Status")
        fig, ax = plt.subplots(figsize=(4, 3))
        status_counts.plot(kind="bar", color=generate_color_palette(len(status_counts)), ax=ax)
        ax.set_title("Status Distribution")
        ax.set_ylabel("Count")
        st.pyplot(fig)

    with col3:
        st.subheader("Tickets by Department")
        fig, ax = plt.subplots(figsize=(4, 3))
        department_counts.plot(kind="bar", color=generate_color_palette(len(department_counts)), ax=ax)
        ax.set_title("Department Distribution")
        ax.set_ylabel("Count")
        st.pyplot(fig)

# Reset Tickets
with st.expander("Reset Tickets (Admin Only)"):
    reset_password = st.text_input("Enter Password to Reset Tickets", type="password")
    if st.button("Reset Tickets"):
        if reset_data(reset_password):
            st.success("Tickets have been reset successfully!")
        else:
            st.error("Incorrect password. Tickets were not reset.")
