🏥 Healthcare Appointment & Follow-up Manager
📖 Overview 

Healthcare Appointment & Follow-up Manager is an AI-powered web application that streamlines the appointment booking process between patients and doctors. The system provides separate portals for Patients, Doctors, and Administrators, while leveraging Large Language Models (LLMs) to generate intelligent pre-visit symptom summaries and post-visit consultation summaries.

It also integrates Google Calendar, Email Notifications, and Medication Reminders to improve communication and patient care.

✨ Features
👨‍⚕️ Patient
Register & Login
Search doctors by specialization
View doctor availability
Book appointments
Cancel & Reschedule appointments
Submit symptoms before appointment
View appointment history
Receive AI-generated visit summaries
Receive medication reminders
🩺 Doctor
Secure Login
View appointments
Read AI symptom summaries
Add prescriptions
Add consultation notes
Generate AI patient-friendly summaries
👨‍💼 Admin
Manage doctors
Manage working hours
Configure slot duration
Mark doctor leave
View appointments
Manage users
🤖 AI Features
Pre-Visit Symptom Analysis
Urgency Detection
Chief Complaint Extraction
Suggested Questions for Doctor
Patient-Friendly Visit Summary
🔔 Notifications
Booking Confirmation
Appointment Reminder
Cancellation Notification
Medication Reminder
Doctor Leave Notification
📅 Google Calendar
Create Calendar Event
Update Event
Delete Event
OAuth2 Authentication
🛠 Tech Stack
Layer	Technology
Frontend	Next.js, React, Tailwind CSS
Backend	FastAPI
Database	PostgreSQL
ORM	SQLAlchemy
Authentication	JWT
AI	OpenAI / Gemini
Scheduler	APScheduler
Email	SMTP / SendGrid
Calendar	Google Calendar API
📂 Project Structure
Healthcare-Appointment-and-Followup-Manager/

backend/
│
├── app/
│   ├── api/
│   ├── auth/
│   ├── database/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── scheduler/
│   ├── notifications/
│   ├── llm/
│   └── main.py
│
├── requirements.txt
└── .env.example

frontend/
│
├── app/
├── components/
├── services/
└── package.json

docs/

screenshots/

README.md
docker-compose.yml
🚀 Setup Guide
1 Clone Repository
git clone https://github.com/hamzak786/Healthcare-Appointment-and-Followup-Manager.git

cd Healthcare-Appointment-and-Followup-Manager
2 Backend Setup
cd backend

python -m venv venv

source venv/bin/activate

# Windows

venv\Scripts\activate

pip install -r requirements.txt
3 Frontend Setup
cd frontend

npm install
4 Configure Environment Variables

Create a .env file using the provided .env.example.

5 Run Backend
uvicorn app.main:app --reload
6 Run Frontend
npm run dev

Backend

http://localhost:8000

Frontend

http://localhost:3000
⚙️ .env.example
DATABASE_URL=postgresql://username:password@localhost:5432/healthcare_db

SECRET_KEY=your_secret_key

JWT_ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=60

OPENAI_API_KEY=your_openai_api_key

SMTP_HOST=smtp.gmail.com

SMTP_PORT=587

SMTP_EMAIL=example@gmail.com

SMTP_PASSWORD=your_password

GOOGLE_CLIENT_ID=

GOOGLE_CLIENT_SECRET=

GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

FRONTEND_URL=http://localhost:3000

BACKEND_URL=http://localhost:8000
📌 API Documentation
Authentication
Method	Endpoint	Description
POST	/register	Register Patient
POST	/login	Login User
POST	/refresh	Refresh JWT Token
Doctors
Method	Endpoint
GET	/doctors
GET	/doctors/{id}
POST	/doctors
PUT	/doctors/{id}
DELETE	/doctors/{id}
Appointments
Method	Endpoint
GET	/appointments
POST	/appointments
PUT	/appointments/{id}
DELETE	/appointments/{id}
AI
Method	Endpoint
POST	/ai/previsit
POST	/ai/postvisit
Notifications
Method	Endpoint
POST	/notifications/send
Google Calendar
Method	Endpoint
POST	/calendar/create
PUT	/calendar/update
DELETE	/calendar/delete
🗄 Database Schema
Users
id
name
email
password
role
created_at
Doctors
id
user_id
specialization
working_hours
slot_duration
Patients
id
user_id
phone
date_of_birth
Appointments
id
patient_id
doctor_id
appointment_date
appointment_time
status
symptoms
ai_summary
Prescriptions
id
appointment_id
medications
notes
Medication Reminders
id
prescription_id
frequency
next_reminder
status
Notifications
id
user_id
type
status
created_at
Doctor Leaves
id
doctor_id
leave_date
reason
🧠 LLM Prompts
Pre-Visit Summary Prompt
Analyze these patient symptoms.

Return:

1. Urgency Level (Low / Medium / High)

2. Chief Complaint

3. Three suggested questions the doctor should ask.

Symptoms:

{{symptoms}}
Post-Visit Summary Prompt
Convert the doctor's notes into a patient-friendly summary.

Return:

• Summary

• Medication Schedule

• Lifestyle Advice

• Follow-up Instructions

Doctor Notes:

{{doctor_notes}}
📅 Google Calendar Setup
Step 1

Go to

Google Cloud Console

Step 2

Create a new project.

Step 3

Enable

Google Calendar API

Step 4

Configure OAuth Consent Screen.

Step 5

Create OAuth Credentials.

Step 6

Add Redirect URI

http://localhost:8000/auth/google/callback
Step 7

Copy

Client ID

Client Secret

into

.env
Step 8

Authenticate the user and obtain access and refresh tokens.

Step 9

Use the Calendar API to:

Create appointment events
Update events when appointments change
Delete events on cancellation
📧 Email Notifications

The system automatically sends:

Booking Confirmation
Appointment Reminder
Appointment Cancellation
Doctor Leave Notification
Medication Reminder
🔒 Security
JWT Authentication
Role-Based Access Control
Password Hashing (bcrypt)
HTTPS Support
Environment Variable Management
OAuth2 for Google Calendar
Input Validation
🚀 Deployment
Component	Platform
Frontend	Vercel
Backend	Render
Database	Neon PostgreSQL
Email	SendGrid
AI	OpenAI / Gemini
📄 License

This project is developed for educational purposes and demonstrates AI-powered healthcare appointment management using modern web technologies and LLM integration.
