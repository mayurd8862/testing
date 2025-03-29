
import streamlit as st
from src.database import save_feedback
import time
import streamlit as st
from streamlit_chat import message
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()
from mongodb import register_user, login_user,get_user_details,place_order,get_user_orders


llm = ChatGroq(model_name="llama-3.3-70b-versatile")
# llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

# Title of the chatbot
st.title("Feedback system")

# Initialize session state for chat history and feedback
if "messages" not in st.session_state:
    st.session_state.messages = []

if "feedback" not in st.session_state:
    st.session_state.feedback = {}

if "username" not in st.session_state:
    st.session_state.username = "mayu" 
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "verified" not in st.session_state:
    st.session_state.verified = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = True
if "last_active_time" not in st.session_state:
    st.session_state.last_active_time = time.time() 

def login_page():
    st.title("🏥 Healthcare E-Commerce Platform")
    st.subheader("", divider="rainbow")
    
    tab1, tab2 = st.tabs(["LOGIN", "REGISTER"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password",type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if login_user(username, password) == 1:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    user_cred = get_user_details(username)
                    st.session_state.user_cred = user_cred
                    st.session_state.user_type = user_cred["usertype"]
                    st.session_state.email = user_cred["mail"]
                    st.success(f"Successfully logged in as {st.session_state.user_type}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with tab2:
        if not st.session_state.verified:
            st.write("🔐Please verify your email to complete the registration process.")
            with st.form("Verify Email"):
                email = st.text_input("Email")
                verify = st.form_submit_button("Verify")
                
                if verify:
                    st.session_state.email = email
        if st.session_state.verified:
            st.write(f"✅ Email verified successfully! - {st.session_state.email}")
            with st.form("register_form"):
                name = st.text_input("Name")
                username = st.text_input("Username")
                # email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                email = st.session_state.email
                user_type = st.selectbox("Select User Type", ["Doctor", "Patient"])
                region = st.selectbox("Select Region", ["India", "USA", "UK", "Canada", "Australia"])

                register = st.form_submit_button("Register")
                
                if register:
                    user_cred = get_user_details(username)
                    st.session_state.user_cred = user_cred
                    msg = register_user(name, username, password, email, user_type, region)
                    if msg["status"] == "success":
                        st.success(msg["message"])
                        user_cred = get_user_details(username)
                        st.session_state.user_cred = user_cred
                    else:
                        st.error(msg["message"])






def analyze_chat_history():
    if "messages" not in st.session_state or len(st.session_state.messages) < 2:
        return "No sufficient chat data to analyze."

    # Format chat messages for LLM
    chat_text = "\n".join(
        [f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages]
    )

    # Prompt for LLM
    messages = [
        ("system", "You are an AI assistant that analyzes chatbot conversations. Your task is to: "
                   "Identify any problems the user is facing. Dont provide any extra information."),
        ("human", f"Here is the conversation:\n\n{chat_text}\n\nAnalyze this and summarize."),
    ]

    # Invoke LLM
    ai_response = llm.invoke(messages)
    
    return ai_response.content

# Function to handle negative feedback
def handle_negative_feedback(index):
    st.session_state[f"show_dialog_{index}"] = True


    # st.write(st.session_state.messages)

# OTP Verification Dialog
@st.dialog("feedback")
def feedback(index,query,res):

    reason = st.text_area(f"🤔Please tell us why this response wasn't helpful")
    if st.button("Submit feedback",use_container_width=True, key=f"submit_feedback_{index}"):
        # if user_otp == st.session_state.otp:
        st.write("✅ Feedback submitted successfully")
        st.session_state[dialog_key] = False
        save_feedback(st.session_state.username, query, res, reason.strip())


# Display chat history
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Add feedback widget only to assistant messages
        if message["role"] == "assistant":
            feedback_key = f"feedback_{i}"
            dialog_key = f"show_dialog_{i}"

            if i > 0 and st.session_state.messages[i - 1]["role"] == "user":
                user_query = st.session_state.messages[i - 1]["content"]
                bot_response = message["content"]
            
                if feedback_key in st.session_state.feedback:
                    st.write(f"😊Feedback: {st.session_state.feedback[feedback_key]}")
                else:
                    sentiment_mapping = [":material/thumb_down:", ":material/thumb_up:"]
                    selected = st.feedback("thumbs", key=feedback_key)
                    
                    # Handle feedback selection
                    if selected is not None and feedback_key not in st.session_state.feedback:
                        st.session_state.feedback[feedback_key] = sentiment_mapping[selected]
                        
                        # If thumbs down (selected = 0), show dialog
                        if selected == 0:
                            st.session_state[dialog_key] = True
                        st.rerun()
            
            # Show dialog for negative feedback
            if dialog_key in st.session_state and st.session_state[dialog_key]:
                feedback(i,user_query, bot_response)
                # with st.popover("Please tell us why this response wasn't helpful"):
                #     feedback_text = st.text_area("Your feedback", key=f"text_feedback_{i}")
                #     if st.button("Submit", key=f"submit_feedback_{i}"):
                #         # Store the detailed feedback
                #         st.session_state[f"detailed_feedback_{i}"] = feedback_text
                #         st.session_state[dialog_key] = False
                #         st.success("Thank you for your feedback!")
                #         st.rerun()


def chatbot_interface():

    with st.sidebar:
        a = st.toggle("Save chat history")
        if a:
            st.session_state.chat_history = True
            st.write(analyze_chat_history())
        else:
            st.session_state.chat_history = False

        with st.expander("Debug: Session State"):
            st.write(st.session_state)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.user_type = None
        st.session_state.messages = []
        st.session_state.order_mode = False
        st.session_state.order_assistant = None
        st.rerun()
    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Add user message to chat history
        st.session_state.last_active_time = time.time()
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Simulate a simple bot response
        bot_response = llm.invoke(f"You are the healthcare e commerce system chatbot. your name is emma. answer the users in a natural tone for the given query. Users Query: {prompt}").content
        # Add bot response to chat history
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
        st.rerun()

    check_inactivity()


def check_inactivity():
    current_time = time.time()
    inactive_time = current_time - st.session_state.last_active_time

    if inactive_time > 10:  # 1 minute warning
        st.toast("⚠️ You have been inactive for a while. Please respond or you will be logged out.", icon="⚠️")

    # if inactive_time > 90:  # 30 seconds after warning → Logout
    #     logout()

def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        chatbot_interface()

if __name__ == "__main__":
    main()