import streamlit as st
from supabase import create_client
import pandas as pd
import os
from dotenv import load_dotenv

# --- 1. SETUP & CONFIGURATION ---
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# Check for secrets
try:
    if not url or not key:
        st.error("🚨 Secrets missing! Check your .env file.")
        st.stop()
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"🚨 Connection Error: {e}")
    st.stop()

# Page Config: Sets the browser tab title and icon
st.set_page_config(
    page_title="TFM Portal",
    page_icon="🦊",
    layout="wide"
)

# BRANDING: Add the Logo to the Sidebar
# ⚠️ Make sure a file named 'logo.png' is in your folder!
try:
    st.logo("logo.png")
except:
    st.warning("⚠️ Logo not found. Make sure you named the file 'logo.png'")


# --- 2. FUNCTIONS ---

def login_user(email, password):
    """Checks database for user credentials"""
    try:
        response = supabase.table('users').select("*").eq('email', email).eq('password', password).execute()
        if len(response.data) > 0:
            return response.data[0]
        return None
    except Exception as e:
        st.error(f"Login System Error: {e}")
        return None

def show_admin_dashboard():
    """The Admin Control Panel"""
    st.title("🎛️ Admin Control Room")
    st.subheader("📅 Live Booking Queue")
    
    # Fetch all bookings
    response = supabase.table('bookings').select("*").order('id').execute()
    rows = response.data
    
    if rows:
        # Display Table
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)
        
        st.divider()
        st.subheader("⚡ Assign Mentor")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            # Select Booking ID
            booking_ids = [row['id'] for row in rows]
            selected_id = st.selectbox("Select Booking ID", booking_ids)
            
        with col2:
            # Select Mentor
            mentors = ["Arjun (IIM-B)", "Simran (IIM-A)", "Rohan (FMS)", "Unassigned"]
            selected_mentor = st.selectbox("Assign Mentor", mentors)
            
        with col3:
            st.write("") # Spacing
            st.write("") # Spacing
            if st.button("✅ Confirm Assignment", type="primary"):
                # Update Database
                supabase.table('bookings').update({
                    'mentor': selected_mentor, 
                    'status': 'Scheduled'
                }).eq('id', selected_id).execute()
                
                st.success(f"Booking #{selected_id} updated!")
                st.rerun()
    else:
        st.info("No bookings found yet.")

def show_student_dashboard(user_email):
    """The Student Booking Panel"""
    st.title("🎓 Student Dashboard")
    st.write(f"Logged in as: {user_email}")
    
    col1, col2 = st.columns(2)
    
    # LEFT: Booking Form
    with col1:
        st.subheader("Book a New Mock")
        with st.form("booking_form"):
            name = st.text_input("Your Full Name")
            notes = st.text_area("Any specific request? (e.g., IIM-B focus)")
            submitted = st.form_submit_button("📅 Request Slot")
            
            if submitted:
                try:
                    # Insert into Database
                    supabase.table('bookings').insert({
                        'student_name': name,
                        'student_email': user_email,
                        'status': 'Pending',
                        'mentor': 'Unassigned'
                    }).execute()
                    st.success("Request Sent! Admin will assign a mentor soon.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error sending request: {e}")

    # RIGHT: Status Table
    with col2:
        st.subheader("My Request Status")
        # Fetch only this student's data
        response = supabase.table('bookings').select("*").eq('student_email', user_email).execute()
        
        if response.data:
            st.table(response.data)
        else:
            st.info("You have no active requests.")

# --- 3. MAIN APP LOGIC ---

# Initialize Session State
if 'user' not in st.session_state:
    st.session_state['user'] = None

# VIEW 1: Login Screen (If user is None)
if st.session_state['user'] is None:
    st.title("🦊 The Fox Mentors")
    st.subheader("Internal Portal Login")
    
    with st.form("login"):
        email = st.text_input("Email")
        pwd = st.text_input("Password", type="password")
        btn = st.form_submit_button("Login Securely")
    
    if btn:
        user = login_user(email, pwd)
        if user:
            st.session_state['user'] = user
            st.rerun()
        else:
            st.error("❌ Invalid Email or Password")

# VIEW 2: Dashboard (If user is Logged In)
else:
    user = st.session_state['user']
    
    # GET ROLE (Safely handle the column name 'type role')
    role = user.get('type role', 'Student') 
    email = user.get('email')
    
    # SIDEBAR INFO
    st.sidebar.write(f"**{role}**")
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