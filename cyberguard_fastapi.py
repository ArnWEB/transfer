# main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import secrets
import uuid
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cyberguard.db")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    opening_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChatFeedback(Base):
    __tablename__ = "chat_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    session_id = Column(String, index=True)
    message_id = Column(String, index=True)
    response_content = Column(Text)
    feedback = Column(String, nullable=True)  # 'like', 'dislike', or null
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Create tables
Base.metadata.create_all(bind=engine)

# FastAPI App
app = FastAPI(title="CyberGuard AI Backend", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    confirmPassword: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    email: str
    created_at: datetime
    updated_at: datetime

class AuthResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    user: Optional[UserResponse] = None

class ChatMessage(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    success: bool
    response: str
    session_id: str

class SessionResponse(BaseModel):
    id: str
    openingMessage: str

class FeedbackSave(BaseModel):
    user_id: int
    session_id: str
    message_id: str
    response_content: str
    feedback: Optional[str] = None

class FeedbackStats(BaseModel):
    total_responses: int
    liked_responses: int
    disliked_responses: int
    like_percentage: float

# Utility Functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

def get_current_user(user_id: int = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# Authentication Routes
@app.post("/api/auth/register", response_model=AuthResponse)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Validate passwords match
    if user_data.password != user_data.confirmPassword:
        return AuthResponse(
            success=False,
            message="Passwords do not match"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        return AuthResponse(
            success=False,
            message="Email already registered"
        )
    
    # Validate password strength (basic validation)
    if len(user_data.password) < 6:
        return AuthResponse(
            success=False,
            message="Password must be at least 6 characters long"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(db_user.id)}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=db_user.id,
        email=db_user.email,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at
    )
    
    return AuthResponse(
        success=True,
        message="Registration successful",
        token=access_token,
        user=user_response
    )

@app.post("/api/auth/login", response_model=AuthResponse)
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    # Find user by email
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user:
        return AuthResponse(
            success=False,
            message="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(user_data.password, user.password_hash):
        return AuthResponse(
            success=False,
            message="Invalid email or password"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        updated_at=user.updated_at
    )
    
    return AuthResponse(
        success=True,
        message="Login successful",
        token=access_token,
        user=user_response
    )

# Chat Routes
@app.post("/api/start-session", response_model=SessionResponse)
def start_session(db: Session = Depends(get_db)):
    session_id = f"session-{uuid.uuid4().hex}"
    opening_message = "🛡️ CyberGuard AI initialized. I'm your cybersecurity assistant. How can I help secure your digital environment today?"
    
    # Create session in database
    db_session = ChatSession(
        id=session_id,
        opening_message=opening_message
    )
    db.add(db_session)
    db.commit()
    
    return SessionResponse(
        id=session_id,
        openingMessage=opening_message
    )

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(message_data: ChatMessage, db: Session = Depends(get_db)):
    # Simulate AI response based on cybersecurity context
    user_message = message_data.message.lower()
    
    # Basic keyword-based responses for demo
    if any(word in user_message for word in ['password', 'passwords']):
        response = "🔐 Password Security Analysis:\n\n• Use unique, complex passwords for each account\n• Enable multi-factor authentication (MFA) wherever possible\n• Consider using a password manager like Bitwarden or 1Password\n• Regularly audit and update passwords\n• Avoid dictionary words and personal information\n\nWould you like specific guidance on password policies or MFA implementation?"
    
    elif any(word in user_message for word in ['phishing', 'email', 'suspicious']):
        response = "🎣 Phishing Protection Protocol:\n\n• Verify sender authenticity before clicking links\n• Check for spelling/grammar errors in emails\n• Hover over links to preview destinations\n• Use email security gateways and anti-phishing tools\n• Implement DMARC, SPF, and DKIM records\n• Conduct regular phishing awareness training\n\nShall I provide a detailed phishing incident response playbook?"
    
    elif any(word in user_message for word in ['firewall', 'network', 'intrusion']):
        response = "🛡️ Network Security Assessment:\n\n• Deploy next-generation firewalls (NGFW)\n• Implement network segmentation and zero-trust architecture\n• Use intrusion detection/prevention systems (IDS/IPS)\n• Monitor traffic with SIEM solutions\n• Regular penetration testing and vulnerability assessments\n• Keep firmware and security policies updated\n\nDo you need assistance with specific firewall configurations?"
    
    elif any(word in user_message for word in ['malware', 'virus', 'ransomware']):
        response = "🦠 Malware Defense Strategy:\n\n• Deploy endpoint detection and response (EDR) solutions\n• Maintain updated antivirus with real-time protection\n• Implement application whitelisting\n• Regular system backups (3-2-1 backup rule)\n• Network traffic monitoring for C2 communications\n• User education on safe browsing practices\n\nWould you like me to detail a ransomware incident response plan?"
    
    elif any(word in user_message for word in ['audit', 'compliance', 'policy']):
        response = "📋 Security Audit & Compliance Framework:\n\n• Conduct regular security assessments (quarterly recommended)\n• Implement controls based on frameworks (NIST, ISO 27001)\n• Document security policies and procedures\n• Perform access reviews and privilege audits\n• Monitor compliance with regulatory requirements\n• Maintain audit trails and logging\n\nWhich compliance framework are you targeting?"
    
    elif any(word in user_message for word in ['breach', 'incident', 'response']):
        response = "🚨 Incident Response Protocol:\n\n• Immediate containment of affected systems\n• Evidence preservation and forensic analysis\n• Stakeholder notification per legal requirements\n• Root cause analysis and remediation\n• Recovery and restoration procedures\n• Post-incident review and lessons learned\n\nDo you have an active incident that requires immediate assistance?"
    
    else:
        response = "🔍 Security Analysis Complete:\n\nI've processed your query through our threat intelligence database. Based on current security best practices, I recommend:\n\n• Implementing defense-in-depth strategies\n• Regular security awareness training\n• Continuous monitoring and threat hunting\n• Keeping all systems updated and patched\n\nCould you provide more specific details about your security concern for a more targeted analysis?"
    
    return ChatResponse(
        success=True,
        response=response,
        session_id=message_data.session_id
    )

# Feedback Routes
@app.post("/api/feedback/save")
def save_feedback(
    feedback_data: FeedbackSave,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if feedback already exists for this message
    existing_feedback = db.query(ChatFeedback).filter(
        ChatFeedback.user_id == feedback_data.user_id,
        ChatFeedback.message_id == feedback_data.message_id
    ).first()
    
    if existing_feedback:
        # Update existing feedback
        existing_feedback.feedback = feedback_data.feedback
        existing_feedback.updated_at = datetime.utcnow()
    else:
        # Create new feedback
        db_feedback = ChatFeedback(
            user_id=feedback_data.user_id,
            session_id=feedback_data.session_id,
            message_id=feedback_data.message_id,
            response_content=feedback_data.response_content,
            feedback=feedback_data.feedback
        )
        db.add(db_feedback)
    
    db.commit()
    
    return {"success": True, "message": "Feedback saved successfully"}

@app.get("/api/feedback/stats", response_model=FeedbackStats)
def get_feedback_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    total = db.query(ChatFeedback).filter(ChatFeedback.user_id == current_user.id).count()
    liked = db.query(ChatFeedback).filter(
        ChatFeedback.user_id == current_user.id,
        ChatFeedback.feedback == "like"
    ).count()
    disliked = db.query(ChatFeedback).filter(
        ChatFeedback.user_id == current_user.id,
        ChatFeedback.feedback == "dislike"
    ).count()
    
    like_percentage = (liked / total * 100) if total > 0 else 0
    
    return FeedbackStats(
        total_responses=total,
        liked_responses=liked,
        disliked_responses=disliked,
        like_percentage=round(like_percentage, 2)
    )

@app.get("/api/feedback/history")
def get_feedback_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    feedback_history = db.query(ChatFeedback).filter(
        ChatFeedback.user_id == current_user.id
    ).order_by(ChatFeedback.created_at.desc()).limit(50).all()
    
    return {
        "success": True,
        "data": [
            {
                "id": feedback.id,
                "session_id": feedback.session_id,
                "message_id": feedback.message_id,
                "response_content": feedback.response_content[:100] + "..." if len(feedback.response_content) > 100 else feedback.response_content,
                "feedback": feedback.feedback,
                "created_at": feedback.created_at,
                "updated_at": feedback.updated_at
            }
            for feedback in feedback_history
        ]
    }

# Health Check
@app.get("/")
def root():
    return {"message": "CyberGuard AI Backend is running", "status": "healthy"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Additional configuration files

# requirements.txt content:
"""
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
pydantic[email]==2.5.0
python-dotenv==1.0.0
"""

# .env file content:
"""
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///./cyberguard.db
# For PostgreSQL: DATABASE_URL=postgresql://username:password@localhost/cyberguard
# For MySQL: DATABASE_URL=mysql://username:password@localhost/cyberguard
"""

# docker-compose.yml for easy deployment:
"""
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=your-super-secret-key-here
      - DATABASE_URL=sqlite:///./cyberguard.db
    volumes:
      - ./cyberguard.db:/app/cyberguard.db
"""

# Dockerfile:
"""
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)