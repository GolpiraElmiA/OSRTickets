import streamlit as st
st.set_page_config(page_title="Support Tickets", page_icon="🎫", layout="wide")

import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Access the key path from environment variable
key_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

# Authenticate with Google Drive API
credentials = Credentials.from_service_account_file(key_path, scopes=['https://www.googleapis.com/auth/drive.file'])
drive_service = build('drive', 'v3', credentials=credentials)

# Define function to upload data to Google Drive
def upload_file(file_path, file_name):
    media = MediaFileUpload(file_path, mimetype='application/vnd.ms-excel')
    request = drive_service.files().create(
        media_body=media,
        body={'name': file_name, 'mimeType': 'application/vnd.ms-excel'}
    )
    response = request.execute()
    return response['id']

def save_to_drive(df, file_name):
    file_path = file_name
    df.to_csv(file_path, index=False)
    assert os.path.exists(file_path), "File not saved locally"
    file_id = upload_file(file_path, file_name)
    return file_id

# Load existing data from Google Drive or create an empty DataFrame if no data exists
def load_data():
    try:
        file_name = 'StatisticalAnalysisTickets.csv'
        query = f"mimeType='application/vnd.ms-excel' and name='{file_name}'"
        result = drive_service.files().list(q=query).execute()

        if result['files']:
            file_id = result['files'][0]['id']
            request = drive_service.files().get_media(fileId=file_id)
            data = request.execute()
            df = pd.read_csv(io.BytesIO(data))
            return df
        else:
            return pd.DataFrame(columns=["ID", "Request Type", "Email", "Department", "Status", "Priority", "Date Submitted", "Summary"])
    except Exception as e:
        st.error(f"Failed to load data from Google Drive. Error: {e}")
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
# Define departments dynamically
departments = [
    "Dentistry and Oral Health", "Ophthalmology", "Orthopaedic", "Pediatric Surgery", 
    "Podiatry", "Transplant Surgery", "Vascular Surgery", "General Surgery",
    "Oral and Maxillofacial", "Otolaryngology", "Plastic Surgery", 
    "Thoracic Surgery", "Urology"
]

# Form for ticket creation
with st.form("add_ticket_form"):
    request_type = st.selectbox(
        "Request Type", 
        ["New", "Follow-up"],
        help="Select whether this is a new request or a follow-up."
    )
    department = st.selectbox(
        "Department", 
        departments,
        help="Choose the department related to this ticket."
    )
    email = st.text_area(
        "Email Address", 
        placeholder="Enter your email address here...",
        help="Provide a valid email address for correspondence."
    )
    issue = st.text_area(
        "Description of the Issue", 
        placeholder="Briefly describe the work or issue you're submitting.",
        help="Include all relevant details to help address your ticket efficiently."
    )
    priority = st.selectbox(
        "Priority Level", 
        ["High", "Medium", "Low"],
        help="Set the priority level for this ticket."
    )
    date_submitted = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = issue[:100]  # Create a brief summary (first 100 characters)

    # Submit button
    submitted = st.form_submit_button("Submit")
    if submitted:
        # Generate a unique ID for the ticket
        ticket_id = f"T{len(st.session_state.df) + 1}"
        # Append the new ticket to the dataframe
        new_ticket = {
            "ID": ticket_id,
            "Request Type": request_type,
            "Email": email,
            "Department": department,
            "Status": "Open",
            "Priority": priority,
            "Date Submitted": date_submitted,
            "Summary": summary,
        }
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_ticket])], ignore_index=True)
        # Save to Google Drive
        save_to_drive(st.session_state.df, 'StatisticalAnalysisTickets.csv')
        st.success(f"Ticket {ticket_id} has been submitted successfully!")

# Display Ticket Table
st.subheader("Submitted Tickets")
st.dataframe(st.session_state.df)

# Ensure the data exists in st.session_state.df
if "df" in st.session_state and not st.session_state.df.empty:
    df = st.session_state.df

    # Calculate ticket insights
    priority_counts = df["Priority"].value_counts()  # Ensure "Priority" exists in your data
    status_counts = df["Status"].value_counts()      # Ensure "Status" exists in your data
    department_counts = df["Department"].value_counts()  # Ensure "Department" exists in your data

    st.header("Ticket Insights")

    # Create three columns for plots
    col1, col2, col3 = st.columns(3)

    # Function to generate a color palette based on the number of categories
    def generate_color_palette(n):
        return sns.color_palette("husl", n)  # You can change the palette type if needed

    # Priority Plot
    with col1:
        st.subheader("Tickets by Priority")
        fig, ax = plt.subplots(figsize=(4, 3))  # Smaller plot size
        priority_colors = generate_color_palette(len(priority_counts))  # Generate palette based on number of categories
        priority_counts.plot(kind="bar", color=priority_colors, ax=ax)
        ax.set_title("Priority Distribution")
        ax.set_ylabel("Count")
        st.pyplot(fig)

    # Status Plot
    with col2:
        st.subheader("Tickets by Status")
        fig, ax = plt.subplots(figsize=(4, 3))  # Smaller plot size
        status_colors = generate_color_palette(len(status_counts))  # Generate palette based on number of categories
        status_counts.plot(kind="bar", color=status_colors, ax=ax)
        ax.set_title("Status Distribution")
        ax.set_ylabel("Count")
        st.pyplot(fig)

    # Department Plot
    with col3:
        st.subheader("Tickets by Department")
        fig, ax = plt.subplots(figsize=(4, 3))  # Smaller plot size
        department_colors = generate_color_palette(len(department_counts))  # Generate palette based on number of categories
        department_counts.plot(kind="bar", color=department_colors, ax=ax)
        ax.set_title("Department Distribution")
        ax.set_ylabel("Count")
        st.pyplot(fig)
else:
    st.warning("No data available to generate insights.")

# Add a button for resetting data
with st.expander("Reset Tickets (Admin Only)"):
    reset_password = st.text_input("Enter Password to Reset Tickets", type="password")
    if st.button("Reset Tickets"):
        if reset_data(reset_password):
            st.success("Tickets have been reset successfully!")
        else:
            st.error("Incorrect password. Tickets were not reset.")
