import streamlit as st
from supabase import create_client
import pandas as pd
import os
from dotenv import load_dotenv

# --- SETUP ---
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

try:
    if not url or not key:
        st.error("🚨 Secrets missing!")
        st.stop()
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"🚨 Connection Error: {e}")
    st.stop()

st.set_page_config(page_title="TFM Portal", layout="wide")

# --- FUNCTIONS ---
def login_user(email, password):
    try:
        response = supabase.table('users').select("*").eq('email', email).eq('password', password).execute()
        if len(response.data) > 0:
            return response.data[0]
        return None
    except:
        return None

# --- ADMIN DASHBOARD ---
def show_admin_dashboard():
    st.title("🎛️ Admin Control Room")
    st.subheader("📅 Live Booking Queue")
    
    response = supabase.table('bookings').select("*").order('id').execute()
    rows = response.data
    
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("⚡ Assign Mentor")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            booking_ids = [row['id'] for row in rows]
            selected_id = st.selectbox("Select Booking ID", booking_ids)
        with col2:
            mentors = ["Arjun (IIM-B)", "Simran (IIM-A)", "Rohan (FMS)", "Unassigned"]
            selected_mentor = st.selectbox("Assign Mentor", mentors)
        with col3:
            st.write("")
            st.write("")
            if st.button("✅ Confirm", type="primary"):
                supabase.table('bookings').update({'mentor': selected_mentor, 'status': 'Scheduled'}).eq('id', selected_id).execute()
                st.success("Updated!")
                st.rerun()
    else:
        st.info("No bookings found yet.")

# --- STUDENT DASHBOARD (NEW!) ---
def show_student_dashboard(user_email):
    st.title("🎓 Student Dashboard")
    st.write(f"Welcome, {user_email}")
    
    col1, col2 = st.columns(2)
    
    # LEFT SIDE: Booking Form
    with col1:
        st.subheader("Book a New Mock")
        with st.form("booking_form"):
            name = st.text_input("Your Full Name")
            # We don't ask for email, we use their login email automatically
            notes = st.text_area("Any specific request? (e.g., IIM-B focus)")
            submitted = st.form_submit_button("📅 Request Slot")
            
            if submitted:
                # INSERT INTO SUPABASE
                try:
                    supabase.table('bookings').insert({
                        'student_name': name,
                        'student_email': user_email,
                        'status': 'Pending',
                        'mentor': 'Unassigned'
                    }).execute()
                    st.success("Request Sent! Admin will assign a mentor soon.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # RIGHT SIDE: My Status
    with col2:
        st.subheader("My Request Status")
        # Fetch only THIS student's bookings
        response = supabase.table('bookings').select("*").eq('student_email', user_email).execute()
        
        if response.data:
            st.table(response.data)
        else:
            st.info("You have no active requests.")

# --- MAIN LOGIC ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

# LOGIN
if st.session_state['user'] is None:
    st.title("🦊 TFM Login")
    with st.form("login"):
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        btn = st.form_submit_button("Enter")
    
    if btn:
        user = login_user(email, pwd)
        if user:
            st.session_state['user'] = user
            st.rerun()
        else:
            st.error("Wrong Password")

# LOGGED IN
else:
    user = st.session_state['user']
    role = user.get('type role', 'Student')
    email = user.get('email')
    
    st.sidebar.write(f"Logged in as: **{role}**")
    if st.sidebar.button("Logout"):
        st.session_state['user'] = None
        st.rerun()

    # ROUTING
    if role == "Admin":
        show_admin_dashboard()
    elif role == "Student":
        show_student_dashboard(email)
    else:
        st.warning("Unknown Role")