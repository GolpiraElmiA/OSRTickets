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
    
    media = MediaFileUpload(file_path, mimetype='text/csv')
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
    return pd.DataFrame(columns=["ID", "Name", "Request Type", "Email", "Section", "Status", "Date Submitted", "Summary"])

# Initialize or load data into session state
if "df" not in st.session_state:
    st.session_state.df = load_data()
    # Ensure the 'Name' column exists

# Reset functionality
def reset_data(password):
    correct_password = "reset123"  # Replace with a secure password
    if password == correct_password:
        st.session_state.df = pd.DataFrame(columns=["ID", "Name", "Request Type", "Email", "Section", "Status", "Date Submitted", "Summary"])
        save_to_drive(st.session_state.df, 'StatisticalAnalysisTickets.csv')
        return True
    return False

# Streamlit page configuration
st.title("Office of Surgical Research | Orthopaedic Trauma Research")
st.header("Statistical Support Request Form")

# Ticket Form
st.subheader("Submit a Support Ticket")
sections = [
    "Dentistry and Oral Health", "Ophthalmology", "Orthopaedic","Dr Schneider's Group", "Pediatric Surgery", 
    "Podiatry", "Transplant Surgery", "Vascular Surgery", "General Surgery",
    "Oral and Maxillofacial", "Oncology","Otolaryngology", "Plastic Surgery", 
    "Thoracic Surgery", "Urology"
]

# Form for ticket creation
with st.form("add_ticket_form"):
    name = st.text_area("Name", placeholder="Please enter your full name here")
    request_type = st.selectbox("Request Type", ["New", "Follow-up"])
    section = st.selectbox("Sections", sections)
    email = st.text_area("Email Address", placeholder="Enter your email address here...")
    issue = st.text_area("Description of the Issue", placeholder="Briefly describe the work or issue you're submitting.")
    date_submitted = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = issue[:5000]  # Create a brief summary (first 5000 characters)

    submitted = st.form_submit_button("Submit")
    if submitted:
        ticket_id = f"T{len(st.session_state.df) + 1}"
        new_ticket = {
            "ID": ticket_id,
            "Name": name,
            "Request Type": request_type,
            "Email": email,
            "Section": sections,
            "Status": "Open",
            "Date Submitted": date_submitted,
            "Summary": summary,
        }
        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_ticket])], ignore_index=True)
        save_to_drive(st.session_state.df, 'StatisticalAnalysisTickets.csv')
        st.success(f"Ticket {ticket_id} has been submitted successfully!")

# Display Ticket Table
st.subheader("_________________________")

###############
# Function to apply color formatting to the 'Status' column
def color_status(val):
    if val == 'In Progress':
        return 'color: blue'
    elif val == 'Open':
        return 'color: green'
    return ''

# Apply the color formatting function to the 'Status' column
styled_df = st.session_state.df.style.applymap(color_status, subset=['Status'])

################################# 31 Jan 2025
st.subheader("Completed Tickets")
df = st.session_state.df
st.session_state.df["Status"] = st.session_state.df["Status"].str.strip().str.title()
df_completed=df[df["Status"].isin(["Completed"])]
st.dataframe(df_completed, use_container_width=True)

st.subheader("Works In Progress/Open")
df_todo = df[df["Status"].isin(["In Progress", "Open"])]
st.dataframe(df_todo.style.applymap(color_status, subset=['Status']), use_container_width=True)
###################################

# Password input for table editing
password_input = st.text_input("Enter password to enable ticket edits", type="password")

if password_input == "reset123":
    # Allow editing only for 'Open' and 'In Progress' tickets
    # status_options = ["Open", "In Progress", "Completed"]
    
    # Filter df_todo for editing
    edited_df_todo = st.data_editor(
        df,
        use_container_width=True,
        num_rows="dynamic",
        key="todo_tickets_table"
    )

    # Update only df_todo in the session state and save changes to Google Drive
    if not edited_df_todo.equals(df_todo):
        df.update(edited_df_todo)  # Update the main DataFrame
        save_to_drive(df, 'StatisticalAnalysisTickets.csv')
        st.success("In Progress/Open tickets updated successfully!")


   

else:
    # Display the table without editing capabilities if password is incorrect or not entered
    st.write("You must enter the correct password to edit the table.")
    # st.dataframe(st.session_state.df)



# Insights section
st.markdown(
    """
    <style>
    .stColumn:nth-child(1) {
        background-color: #e1f2ea;
        padding-top: 20px;
        padding-left: 20px;
        padding-right: 20px;
    }
    .stColumn:nth-child(2){
        padding-top: 20px;
        padding-left: 20px;
        padding-right: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


if not st.session_state.df.empty:
    df = st.session_state.df
    status_counts = df["Status"].value_counts()
    section_counts = df["Section"].value_counts()

    #################### st.header("Ticket Insights")####################

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Tickets by Status")
        for status, count in status_counts.items():
            st.write(f"**{status}:** {count} tickets")

    with col2:
        colors=sns.color_palette("light:#5A9", len(section_counts))
        st.subheader("Tickets by Section")
        fig, ax = plt.subplots(figsize=(2, 2))
        section_counts.plot(kind="pie", colors=colors, labels=section_counts.index, textprops={'fontsize': 4}, ax=ax)
        ax.set_ylabel('')
        st.pyplot(fig)

# Reset Tickets
with st.expander("Reset Tickets (Admin Only)"):
    reset_password = st.text_input("Enter Password to Reset Tickets", type="password")
    if st.button("Reset Tickets"):
        if reset_data(reset_password):
            st.success("Tickets have been reset successfully!")
        else:
            st.error("Incorrect password. Tickets were not reset.")
