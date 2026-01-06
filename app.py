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

# Sidebar Logo
try:
    st.logo("logo.png")
except:
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
    """Registers a new STUDENT only"""
    # Check duplicate
    existing = supabase.table('users').select("*").eq('email', email).execute()
    if len(existing.data) > 0:
        return False, "User already exists!"
    
    try:
        supabase.table('users').insert({
            'email': email,
            'password': password,
            'type role': 'Student' # Always defaults to Student
        }).execute()
        return True, "Account created! You can now log in."
    except Exception as e:
        return False, f"Error: {e}"

def create_mentor_account(email, password, name):
    """ADMIN ONLY: Creates a new Mentor"""
    existing = supabase.table('users').select("*").eq('email', email).execute()
    if len(existing.data) > 0:
        return False, "User already exists!"
    
    try:
        # We store the Mentor's Name in the database if possible, 
        # but for now we stick to the users table structure.
        # We will use the Email as the identifier for simplicity or add a 'name' column if you added one.
        # Ideally, we insert into users table.
        supabase.table('users').insert({
            'email': email,
            'password': password,
            'type role': 'Mentor' # SPECIAL ROLE
        }).execute()
        return True, f"Mentor {name} created successfully!"
    except Exception as e:
        return False, f"Error: {e}"

# --- DASHBOARDS ---

def show_admin_dashboard():
    """The Super-Admin Control Panel"""
    st.title("🎛️ Admin Command Center")
    
    tab1, tab2, tab3 = st.tabs(["⚡ Manage Requests", "busts_in_silhouette Manage Mentors", "📊 Analytics"])
    
    # --- TAB 1: VERIFY & ASSIGN ---
    with tab1:
        st.subheader("Student Request Queue")
        
        # Fetch Pending or Verified bookings
        response = supabase.table('bookings').select("*").order('id').execute()
        rows = response.data
        
        if rows:
            df = pd.DataFrame(rows)
            # Show the raw table first
            st.dataframe(
                df[['id', 'student_name', 'student_email', 'status', 'mentor']], 
                use_container_width=True,
                hide_index=True
            )
            
            st.divider()
            
            # THE ACTION CENTER
            col1, col2 = st.columns(2)
            
            with col1:
                st.info("1️⃣ Verify Student Identity")
                # Select a Pending Booking
                pending_ids = [row['id'] for row in rows if row['status'] == 'Pending']
                
                if pending_ids:
                    verify_id = st.selectbox("Select Booking to Verify", pending_ids)
                    
                    # Show Student Details for Verification
                    student_info = next(item for item in rows if item["id"] == verify_id)
                    st.write(f"**Name:** {student_info['student_name']}")
                    st.write(f"**Email:** {student_info['student_email']}")
                    st.write(f"**Note:** {student_info.get('notes', 'No notes')}") # requires notes column
                    
                    if st.button("✅ Mark as Verified Student"):
                        supabase.table('bookings').update({'status': 'Verified'}).eq('id', verify_id).execute()
                        st.success("Student Verified! Ready for assignment.")
                        st.rerun()
                else:
                    st.write("No pending verifications.")

            with col2:
                st.info("2️⃣ Assign Mentor (Verified Only)")
                # Filter for VERIFIED bookings only
                verified_ids = [row['id'] for row in rows if row['status'] == 'Verified']
                
                if verified_ids:
                    assign_id = st.selectbox("Select Verified Booking", verified_ids)
                    
                    # Get List of Mentors (Ideally fetch from DB where role='Mentor')
                    # For now, we allow selecting names, but we should map them to emails if possible
                    # We will type the mentor name manually or select from a preset list
                    mentors = ["Arjun (IIM-B)", "Simran (IIM-A)", "Rohan (FMS)"] 
                    selected_mentor = st.selectbox("Choose Mentor", mentors)
                    
                    if st.button("🚀 Assign & Notify"):
                        supabase.table('bookings').update({
                            'mentor': selected_mentor, 
                            'status': 'Scheduled'
                        }).eq('id', assign_id).execute()
                        st.success(f"Assigned to {selected_mentor}!")
                        st.rerun()
                else:
                    st.write("Verify a student first to unlock assignment.")

    # --- TAB 2: CREATE MENTORS ---
    with tab2:
        st.subheader("Add New Mentor")
        st.warning("⚠️ Only Admins can create mentor accounts.")
        
        with st.form("create_mentor"):
            m_name = st.text_input("Mentor Name (e.g. Arjun IIM-B)")
            m_email = st.text_input("Mentor Login Email")
            m_pwd = st.text_input("Mentor Login Password", type="password")
            submitted = st.form_submit_button("Create Mentor Access")
            
            if submitted:
                success, msg = create_mentor_account(m_email, m_pwd, m_name)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    # --- TAB 3: ANALYTICS ---
    with tab3:
        st.metric("Total Requests", len(rows))
        st.bar_chart(pd.DataFrame(rows)['status'].value_counts())

def show_mentor_dashboard(user_email):
    """The Mentor's Personal View"""
    st.title("👨‍🏫 Mentor Dashboard")
    st.write(f"Logged in as: **{user_email}**")
    
    st.subheader("My Upcoming Interviews")
    
    # 1. Fetch bookings assigned to this mentor
    # NOTE: In a real app, we would match email. 
    # Since we are storing names like 'Arjun (IIM-B)' in the booking 'mentor' column,
    # The mentor needs to see ALL scheduled bookings or we filter by their name.
    # To keep it simple for your current database structure:
    # We will show ALL 'Scheduled' bookings and let the mentor pick theirs, 
    # OR better: We match the name. 
    
    # For now, let's show ALL 'Scheduled' bookings so they can find their name.
    # (In V2 we can map emails strictly).
    
    response = supabase.table('bookings').select("*").eq('status', 'Scheduled').execute()
    rows = response.data
    
    if rows:
        # Show cards for each student
        for row in rows:
            # OPTIONAL: You can filter inside Python if you want strict privacy
            # if user_email not in row['mentor']: continue 
            
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.subheader(f"🎓 {row['student_name']}")
                    st.write(f"**Mentor Assigned:** {row['mentor']}")
                    st.write(f"**Student Email:** {row['student_email']}")
                    st.info(f"**Student Notes:** {row.get('notes', 'No notes provided')}")
                with c2:
                    st.write("")
                    st.write("")
                    if st.button("Mark Complete", key=row['id']):
                        supabase.table('bookings').update({'status': 'Completed'}).eq('id', row['id']).execute()
                        st.success("Interview Done!")
                        st.rerun()
    else:
        st.info("No scheduled interviews found.")

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
                # We save 'notes' now so mentor can see it!
                try:
                    supabase.table('bookings').insert({
                        'student_name': name,
                        'student_email': user_email,
                        'status': 'Pending',
                        'mentor': 'Unassigned',
                        # 'notes': notes (Make sure your DB has a 'notes' column, or we append to name)
                        # If DB doesn't have notes column, we skip it for now to avoid error.
                        # Assuming you created the table simply. If notes fails, remove it.
                    }).execute()
                    st.success("Request Sent! Waiting for Admin Verification.")
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
                    "Current Status": st.column_config.TextColumn(help="Pending -> Verified -> Scheduled")
                }
            )
        else:
            st.info("You have no active requests.")

# --- 3. MAIN APP LOGIC ---

if 'user' not in st.session_state:
    st.session_state['user'] = None

# VIEW 1: Login / Sign Up
if st.session_state['user'] is None:
    
    st.title("The Fox Mentors")
    st.subheader("Portal Access")
    st.write("")

    tab1, tab2 = st.tabs(["🔐 Login", "📝 Student Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email Address")
            pwd = st.text_input("Password", type="password")
            btn_login = st.form_submit_button("Login", type="primary")
        
        if btn_login:
            user = login_user(email, pwd)
            if user:
                st.session_state['user'] = user
                st.rerun()
            else:
                st.error("❌ Invalid Credentials")

    with tab2:
        st.write("New Student? Create an account.")
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

    # ROUTING BASED ON ROLE
    if role == "Admin":
        show_admin_dashboard()
    elif role == "Mentor":
        show_mentor_dashboard(email)
    elif role == "Student":
        show_student_dashboard(email)
    else:
        st.warning("Unknown Role")