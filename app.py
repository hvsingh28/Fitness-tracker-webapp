import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import time
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

# Set Page Configuration
st.set_page_config(page_title="Personal Fitness Tracker", layout="wide")

# Custom CSS
st.markdown("""
    <style>
        body { background-color: #f5f5f5; font-family: 'Arial', sans-serif; }
        .stButton > button { background-color: #ff4b4b; color: white; font-size: 18px; padding: 10px; }
        .stTitle { color: #ff4b4b; font-size: 24px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Database Connection
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# Create Users Table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        age INTEGER,
        height FLOAT,
        weight FLOAT,
        gender TEXT
    )
''')

# Create Records Table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        date TEXT,
        bmi FLOAT,
        duration INTEGER,
        heart_rate INTEGER,
        body_temp FLOAT,
        calories FLOAT
    )
''')
conn.commit()

# User Authentication Functions
def register_user(username, password, age, height, weight, gender):
    try:
        cursor.execute("INSERT INTO users (username, password, age, height, weight, gender) VALUES (?, ?, ?, ?, ?, ?)",
                       (username, password, age, height, weight, gender))
        conn.commit()
        return True
    except:
        return False

def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

def update_user(username, age, height, weight, gender):
    cursor.execute("UPDATE users SET age=?, height=?, weight=?, gender=? WHERE username=?", (age, height, weight, gender, username))
    conn.commit()

# Load Dataset
calories_df = pd.read_csv(r"calories.csv")
exercise_df = pd.read_csv(r"exercise.csv")

# Merge Data
exercise_df = exercise_df.merge(calories_df, on="User_ID")
exercise_df["BMI"] = exercise_df["Weight"] / ((exercise_df["Height"] / 100) ** 2)
exercise_df.drop(columns=["User_ID"], inplace=True)

# Train Model
X = exercise_df[["Gender", "Age", "BMI", "Duration", "Heart_Rate", "Body_Temp"]]
y = exercise_df["Calories"]
X = pd.get_dummies(X, drop_first=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)
model = RandomForestRegressor(n_estimators=100, max_depth=6)
model.fit(X_train, y_train)

# Sidebar - User Login & Registration
st.sidebar.title("Welcome to Fitness Tracker! 💪")
menu = st.sidebar.radio("Menu", ["Login", "Register"])

if menu == "Register":
    st.sidebar.subheader("Create an Account")
    reg_username = st.sidebar.text_input("Username")
    reg_password = st.sidebar.text_input("Password", type="password")
    reg_age = st.sidebar.number_input("Age", 10, 100, value=25)
    reg_height = st.sidebar.number_input("Height (cm)", 100.0, 250.0, value=170.0)
    reg_weight = st.sidebar.number_input("Weight (kg)", 30.0, 200.0, value=70.0)
    reg_gender = st.sidebar.selectbox("Gender", ["Male", "Female"])

    if st.sidebar.button("Register"):
        if register_user(reg_username, reg_password, reg_age, reg_height, reg_weight, reg_gender):
            st.sidebar.success("✅ Account Created! You can now login.")
        else:
            st.sidebar.error("❌ Username already exists!")

elif menu == "Login":
    st.sidebar.subheader("Login to Your Account")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    
    if st.sidebar.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state["user"] = user
            st.success(f"✅ Welcome, {username}! Redirecting...")
            time.sleep(1)
            st.rerun()
        else:
            st.sidebar.error("❌ Invalid Credentials!")

# Main App Content
if "user" in st.session_state:
    user_data = st.session_state["user"]
    st.title(f"Hello, {user_data[1]}! 👋")

    # Buttons to Show Profile & Past Records
    show_past_records = st.button("📊 Display Past Records")

    # Profile Section (Only When Clicked)
    # Check if session_state for profile visibility exists, else set default
    if "show_profile" not in st.session_state:
        st.session_state["show_profile"] = False

    # Button to toggle profile section with a unique key
    if st.button("📌 View Profile", key="view_profile_btn"):
        st.session_state["show_profile"] = not st.session_state["show_profile"]

    # Display profile only if the user clicks the button
    if st.session_state["show_profile"]:
        st.header("Your Profile")

        new_age = st.number_input("Age", 10, 100, value=user_data[3], key="age_input")
        new_height = st.number_input("Height (cm)", 100.0, 250.0, value=user_data[4], key="height_input")
        new_weight = st.number_input("Weight (kg)", 30.0, 200.0, value=user_data[5], key="weight_input")
        new_gender = st.selectbox("Gender", ["Male", "Female"], index=0 if user_data[6] == "Male" else 1, key="gender_select")

        # Unique key for update button
        if st.button("Update Profile", key="update_profile_btn"):
            update_user(user_data[1], new_age, new_height, new_weight, new_gender)
            st.success("✅ Profile updated successfully!")
            user_data = login_user(user_data[1], user_data[2])  # Refresh user data
            st.session_state["user"] = user_data  # Update session state

    # User Input for Predictions
    st.header("Enter Your Workout Details")
    duration = st.slider("Duration (min)", 0, 60, 30)
    heart_rate = st.slider("Heart Rate", 60, 180, 90)
    body_temp = st.slider("Body Temperature (°C)", 35.0, 42.0, 37.0)
    bmi = user_data[5] / ((user_data[4] / 100) ** 2)

    input_data = pd.DataFrame([[user_data[3], bmi, duration, heart_rate, body_temp, user_data[6]]],
                              columns=["Age", "BMI", "Duration", "Heart_Rate", "Body_Temp", "Gender"])
    input_data = pd.get_dummies(input_data, drop_first=True)
    for col in X_train.columns:
        if col not in input_data.columns:
            input_data[col] = 0
    input_data = input_data[X_train.columns]
    prediction = model.predict(input_data)[0]
    
    st.success(f"🔥 Estimated Calories Burned: {round(prediction, 2)} kcal")

    # Save Workout Data
    if st.button("💾 Save This Record"):
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO records (username, date, bmi, duration, heart_rate, body_temp, calories) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (user_data[1], date, bmi, duration, heart_rate, body_temp, prediction))
        conn.commit()
        st.success("✅ Workout record saved successfully!")

    # Display Past Records (Only When Clicked)
    if show_past_records:
        cursor.execute("SELECT date, bmi, duration, heart_rate, body_temp, calories FROM records WHERE username = ? ORDER BY id DESC LIMIT 3", (user_data[1],))
        past_records = cursor.fetchall()
        st.table(pd.DataFrame(past_records, columns=["Date", "BMI", "Duration", "Heart Rate", "Body Temp", "Calories"]))
    # AI-based Suggestions
    st.header("🍽️ AI-Powered suggestions")
    if bmi < 18.5:
        st.info("**AI Suggestion: Increase caloric intake with healthy fats & proteins (nuts, dairy, peanut butter). Strength training recommended.**")
    elif 18.5 <= bmi < 25:
        st.info("**AI Suggestion: Maintain balanced diet with a mix of cardio & strength training. Ensure micronutrient intake (B12, Iron, Magnesium).**")
    elif 25 <= bmi < 30:
        st.warning("**AI Suggestion: Increase cardio-based exercises (running, HIIT). Reduce processed sugar & refined carbs. Track daily calorie intake.**")
    else:
        st.error("**AI Suggestion: Focus on high-intensity workouts (HIIT, circuit training). Follow low-carb, high-protein diet. Increase water intake.**")

    if heart_rate < 60:
        st.warning("**AI Suggestion: Increase cardio intensity to improve heart health. Ensure proper electrolyte intake (potassium, magnesium).**")
    elif heart_rate > 100:
        st.error("**AI Suggestion: Reduce caffeine & energy drinks. Incorporate cool-down exercises and avoid overtraining.**")

    if prediction < 200:
        st.warning("**AI Suggestion: Increase workout intensity or extend duration. Try HIIT for better calorie burn.**")
    elif prediction > 500:
        st.success("**AI Suggestion: Stay hydrated and replenish lost glycogen with healthy carbs (oats, fruits, sweet potatoes).**")
    # AI-Based Personalized Meal Plan
    st.header("🍽️ AI-Powered Personalized Meal Plan")

    # Fetch the last three records
    cursor.execute("SELECT bmi, heart_rate, calories FROM records WHERE username = ? ORDER BY id DESC LIMIT 3", (user_data[1],))
    past_records = cursor.fetchall()

    if past_records:
        avg_bmi = np.mean([record[0] for record in past_records])
        avg_heart_rate = np.mean([record[1] for record in past_records])
        avg_calories = np.mean([record[2] for record in past_records])

        meal_plan = ""
        
        # Meal Plan based on BMI
        if avg_bmi < 18.5:
            meal_plan += "🔹 **You are underweight.** Focus on high-protein and high-calorie foods like nuts, dairy, and whole grains.\n"
        elif avg_bmi > 25:
            meal_plan += "🔹 **You are overweight.** Opt for fiber-rich foods, lean proteins, and avoid processed sugars.\n"
        else:
            meal_plan += "🔹 **You have a healthy BMI.** Maintain a balanced diet with proteins, carbs, and healthy fats.\n"

        # Meal Plan based on Heart Rate
        if avg_heart_rate > 100:
            meal_plan += "🔹 **Your heart rate is high.** Include potassium-rich foods like bananas and spinach to regulate heart function.\n"
        elif avg_heart_rate < 60:
            meal_plan += "🔹 **Your heart rate is low.** Increase your intake of iron-rich foods like lentils and dark leafy greens.\n"

        # Meal Plan based on Calories Burned
        if avg_calories > 500:
            meal_plan += "🔹 **You're burning a lot of calories!** Increase protein intake with chicken, tofu, or fish for muscle recovery.\n"
        elif avg_calories < 200:
            meal_plan += "🔹 **Low calorie burn detected.** Consider incorporating more complex carbs like quinoa and brown rice for sustained energy.\n"

        st.success(meal_plan)
    else:
        st.info("No past records found. Start logging workouts to get personalized meal plans!")
        
