#!/usr/bin/env python
"""Create admin user directly in database for demo purposes."""
import sys
sys.path.insert(0, r'c:\healthcare manager\healthcare-backend')

from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.utils.security import hash_password

db = SessionLocal()

# Check if admin already exists
existing = db.query(User).filter(User.email == 'admin@example.com').first()
if existing:
    print(f"✅ Admin already exists - ID: {existing.id}")
else:
    # Create admin user
    admin = User(
        email='admin@example.com',
        hashed_password=hash_password('Admin@123'),
        full_name='Administrator',
        role=RoleEnum.ADMIN
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    print(f"✅ Admin created - ID: {admin.id}, Email: {admin.email}")

db.close()
