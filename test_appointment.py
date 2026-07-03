#!/usr/bin/env python
"""Test appointment booking."""
import requests
from datetime import datetime, timedelta

print('=== STEP 8: Book Appointment ===')
print()

# Get patient token
print('1. Getting patient token...')
response = requests.post(
    'http://127.0.0.1:8000/auth/login',
    json={'email': 'hamza@gmail.com', 'password': 'Hamza@123'}
)
patient_token = response.json()['access_token']
print('   ✅ Token obtained')

# Get patient UUID
print('2. Getting patient UUID...')
response = requests.get(
    'http://127.0.0.1:8000/patients',
    headers={'Authorization': f'Bearer {patient_token}'}
)
if response.status_code == 200:
    data = response.json()
    if data['results']:
        patient_uuid = data['results'][0]['patient_id']
        print(f'   ✅ Patient UUID: {patient_uuid}')
    else:
        print('   ❌ No patient found')
else:
    print(f'   ❌ Error: {response.text}')

# Book appointment
print('3. Booking appointment...')
doctor_uuid = '882cb088-7e6e-42a7-85b0-7eee7b434a93'
tomorrow = (datetime.now() + timedelta(days=1)).date()

response = requests.post(
    'http://127.0.0.1:8000/appointments',
    json={
        'doctor_id': doctor_uuid,
        'patient_id': patient_uuid,
        'appointment_date': str(tomorrow),
        'appointment_time': '10:00'
    },
    headers={'Authorization': f'Bearer {patient_token}'}
)
print(f'   Status: {response.status_code}')
if response.status_code == 201:
    appointment = response.json()
    print('   ✅ Appointment booked!')
    print(f'      ID: {appointment.get("appointment_id")}')
    print(f'      Date: {appointment.get("appointment_date")}')
    print(f'      Time: {appointment.get("appointment_time")}')
else:
    print(f'   ❌ Error: {response.text}')
