import streamlit as st
from supabase import create_client
import pandas as pd
import os
from dotenv import load_dotenv

# --- 1. SETUP & CONFIGURATION ---
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

try:
    if not url or not key:
        st.error("🚨 Secrets missing! Check your .env file.")
        st.stop()
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"🚨 Connection Error: {e}")
    st.stop()

st.set_page_config(
    page_title="TFM Portal",
    page_icon="🦊",
    layout="wide"
)

# Sidebar Logo (Small and discreet in the corner)
try:
    st.logo("logo.png")
except:
    # If no logo file, just show text in sidebar
    st.sidebar.write("🦊 The Fox Mentors")


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

def register_user(email, password):
    """Registers a new student"""
    # 1. Check if user already exists
    existing = supabase.table('users').select("*").eq('email', email).execute()
    if len(existing.data) > 0:
        return False, "User already exists!"
    
    # 2. Add new user
    try:
        supabase.table('users').insert({
            'email': email,
            'password': password,
            'type role': 'Student' # Default role
        }).execute()
        return True, "Account created! You can now log in."
    except Exception as e:
        return False, f"Error: {e}"

def show_admin_dashboard():
    """The Admin Control Panel"""
    st.title("🎛️ Admin Control Room")
    
    # Fetch Data
    response = supabase.table('bookings').select("*").order('id').execute()
    rows = response.data
    
    if rows:
        st.subheader(f"📅 Live Booking Queue ({len(rows)})")
        df = pd.DataFrame(rows)
        
        display_df = df[['id', 'student_name', 'mentor', 'status', 'created_at']]
        display_df.columns = ["ID", "Student Name", "Assigned Mentor", "Status", "Timestamp"]
        
        st.dataframe(
            display_df, 
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Pending", "Scheduled", "Completed"],
                    width="medium"
                ),
                "Timestamp": st.column_config.DatetimeColumn(
                    "Request Time",
                    format="D MMM, h:mm a"
                )
            }
        )
        
        st.divider()
        st.subheader("⚡ Quick Actions")
        
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
            if st.button("✅ Confirm Assignment", type="primary"):
                supabase.table('bookings').update({
                    'mentor': selected_mentor, 
                    'status': 'Scheduled'
                }).eq('id', selected_id).execute()
                st.success(f"Booking #{selected_id} updated!")
                st.rerun()
    else:
        st.info("No active bookings found.")

def show_student_dashboard(user_email):
    """The Student Booking Panel"""
    st.title("🎓 Student Dashboard")
    st.write(f"Logged in as: **{user_email}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.container(border=True) 
        st.subheader("Book a New Mock")
        with st.form("booking_form"):
            name = st.text_input("Your Full Name")
            notes = st.text_area("Any specific request? (e.g., IIM-B focus)")
            submitted = st.form_submit_button("📅 Request Slot", type="primary")
            
            if submitted:
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
                    st.error(f"Error sending request: {e}")

    with col2:
        st.subheader("My Request Status")
        response = supabase.table('bookings').select("*").eq('student_email', user_email).order('id', desc=True).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            display_df = df[['created_at', 'mentor', 'status']]
            display_df.columns = ["Requested On", "Assigned Mentor", "Current Status"]
            
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Requested On": st.column_config.DatetimeColumn(format="D MMM, h:mm a"),
                    "Current Status": st.column_config.TextColumn(help="Wait for 'Scheduled'")
                }
            )
        else:
            st.info("You have no active requests. Book one on the left!")

# --- 3. MAIN APP LOGIC ---

if 'user' not in st.session_state:
    st.session_state['user'] = None

# VIEW 1: Login / Sign Up Screen
if st.session_state['user'] is None:
    
    # Simple Text Header (No Big Image)
    st.title("The Fox Mentors")
    st.subheader("Internal Portal Login")
    st.write("")

    # TABS for Login vs Sign Up
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    # --- TAB 1: LOGIN ---
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email Address")
            pwd = st.text_input("Password", type="password")
            btn_login = st.form_submit_button("Login Securely", type="primary")
        
        if btn_login:
            user = login_user(email, pwd)
            if user:
                st.session_state['user'] = user
                st.rerun()
            else:
                st.error("❌ Invalid Email or Password")

    # --- TAB 2: SIGN UP ---
    with tab2:
        st.write("New Student? Create an account here.")
        with st.form("signup_form"):
            new_email = st.text_input("Enter Email")
            new_pwd = st.text_input("Create Password", type="password")
            btn_signup = st.form_submit_button("Create Account")
        
        if btn_signup:
            if new_email and new_pwd:
                success, message = register_user(new_email, new_pwd)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.warning("Please fill in both fields.")

# VIEW 2: Dashboard
else:
    user = st.session_state['user']
    role = user.get('type role', 'Student') 
    email = user.get('email')
    
    st.sidebar.write(f"Logged in as: **{role}**")
    
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    if role == "Admin":
        show_admin_dashboard()
    elif role == "Student":
        show_student_dashboard(email)
    else:
        st.warning("Unknown Role")