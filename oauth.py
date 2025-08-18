# main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
import jwt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.exc import IntegrityError
import os
from enum import Enum
import logging
from contextlib import asynccontextmanager
import secrets
from passlib.context import CryptContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./oauth_system.db")
    
settings = Settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database setup
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Role enumeration
class RoleEnum(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"

# Association table for many-to-many relationship between users and roles
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('role_id', Integer, ForeignKey('roles.id'))
)

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user")

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

# Pydantic Models
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str
    roles: Optional[List[RoleEnum]] = [RoleEnum.USER]
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    roles: List[str]
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    roles: Optional[List[RoleEnum]] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    roles: Optional[List[str]] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Custom Exceptions
class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class ValidationError(HTTPException):
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# OAuth2 scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class AuthService:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(user_id: int, db: Session):
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        token_data = {"user_id": user_id, "exp": expires_at, "type": "refresh"}
        token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        
        # Store refresh token in database
        db_token = RefreshToken(
            token=token,
            user_id=user_id,
            expires_at=expires_at
        )
        db.add(db_token)
        db.commit()
        return token
    
    @staticmethod
    def verify_token(token: str) -> TokenData:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            email: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            roles: List[str] = payload.get("roles", [])
            token_type: str = payload.get("type")
            
            if email is None or user_id is None:
                raise AuthenticationError("Invalid token")
            
            return TokenData(email=email, user_id=user_id, roles=roles)
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.JWTError:
            raise AuthenticationError("Invalid token")

class UserService:
    @staticmethod
    def get_user_by_email(db: Session, email: str):
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str):
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int):
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create_user(db: Session, user_create: UserCreate, created_by_admin: bool = False):
        try:
            hashed_password = AuthService.get_password_hash(user_create.password)
            db_user = User(
                email=user_create.email,
                username=user_create.username,
                hashed_password=hashed_password,
                is_verified=created_by_admin  # Auto-verify if created by admin
            )
            
            # Assign roles
            for role_name in user_create.roles:
                role = db.query(Role).filter(Role.name == role_name.value).first()
                if role:
                    db_user.roles.append(role)
            
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            return db_user
        except IntegrityError:
            db.rollback()
            raise ValidationError("User with this email or username already exists")
    
    @staticmethod
    def authenticate_user(db: Session, username: str, password: str):
        # Try to find user by email or username
        user = UserService.get_user_by_email(db, username)
        if not user:
            user = UserService.get_user_by_username(db, username)
        
        if not user:
            return False
        if not user.is_active:
            raise AuthenticationError("User account is deactivated")
        if not AuthService.verify_password(password, user.hashed_password):
            return False
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        return user
    
    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate):
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        update_data = user_update.dict(exclude_unset=True)
        
        # Handle roles separately
        if "roles" in update_data:
            roles = update_data.pop("roles")
            user.roles.clear()
            for role_name in roles:
                role = db.query(Role).filter(Role.name == role_name.value).first()
                if role:
                    user.roles.append(role)
        
        # Update other fields
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

# Authentication dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    token_data = AuthService.verify_token(token)
    user = UserService.get_user_by_id(db, token_data.user_id)
    
    if user is None:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is deactivated")
    
    return user

# Role-based access control
def require_roles(allowed_roles: List[RoleEnum]):
    def decorator(current_user: User = Depends(get_current_user)):
        user_roles = [role.name for role in current_user.roles]
        if not any(role.value in user_roles for role in allowed_roles):
            raise AuthorizationError(
                f"Access denied. Required roles: {[role.value for role in allowed_roles]}"
            )
        return current_user
    return decorator

# Initialize database
def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Create default roles
    db = SessionLocal()
    try:
        for role_name in RoleEnum:
            existing_role = db.query(Role).filter(Role.name == role_name.value).first()
            if not existing_role:
                role = Role(
                    name=role_name.value,
                    description=f"Default {role_name.value} role"
                )
                db.add(role)
        
        # Create default admin user
        admin_email = "admin@example.com"
        existing_admin = db.query(User).filter(User.email == admin_email).first()
        if not existing_admin:
            admin_user = User(
                email=admin_email,
                username="admin",
                hashed_password=AuthService.get_password_hash("Admin123!"),
                is_verified=True
            )
            admin_role = db.query(Role).filter(Role.name == RoleEnum.ADMIN).first()
            if admin_role:
                admin_user.roles.append(admin_role)
            db.add(admin_user)
        
        db.commit()
        logger.info("Database initialized successfully")
        logger.info("Default admin credentials - Email: admin@example.com, Password: Admin123!")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    pass

# Custom OpenAPI schema for better Swagger documentation
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="OAuth API System",
        version="1.0.0",
        description="""
        Production-ready FastAPI OAuth system with JWT tokens and role-based access control.
        
        ## Authentication
        
        1. Use the `/auth/login` endpoint to get your access token
        2. Click the "Authorize" button and enter your token
        3. Access protected endpoints based on your role
        
        ## Default Credentials
        - **Admin**: admin@example.com / Admin123!
        
        ## Roles
        - **admin**: Full system access
        - **manager**: Management operations
        - **user**: Basic user operations
        - **guest**: Read-only access
        """,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# FastAPI app
app = FastAPI(
    title="OAuth API System",
    description="Production-ready FastAPI OAuth system with JWT tokens and role-based access control",
    version="1.0.0",
    lifespan=lifespan
)

# Set custom OpenAPI
app.openapi = custom_openapi

# Exception handlers
@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "authentication_error", "message": exc.detail},
        headers=exc.headers
    )

@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "authorization_error", "message": exc.detail}
    )

@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "validation_error", "message": exc.detail}
    )

# Authentication routes
@app.post("/auth/login", response_model=Token, tags=["Authentication"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login with username/email and password to get access token.
    Use this token in the Authorization header: Bearer <token>
    """
    try:
        user = UserService.authenticate_user(db, form_data.username, form_data.password)
        if not user:
            raise AuthenticationError("Incorrect email/username or password")
        
        # Create tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={
                "sub": user.email,
                "user_id": user.id,
                "roles": [role.name for role in user.roles]
            },
            expires_delta=access_token_expires
        )
        
        refresh_token = AuthService.create_refresh_token(user.id, db)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    except AuthenticationError:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/auth/refresh", response_model=Token, tags=["Authentication"])
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        payload = jwt.decode(
            refresh_request.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")
        
        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationError("Invalid token")
        
        # Check if refresh token exists and is not revoked
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_request.refresh_token,
            RefreshToken.is_revoked == False
        ).first()
        
        if not db_token or db_token.expires_at < datetime.utcnow():
            raise AuthenticationError("Refresh token is invalid or expired")
        
        # Get user
        user = UserService.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        # Create new tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={
                "sub": user.email,
                "user_id": user.id,
                "roles": [role.name for role in user.roles]
            },
            expires_delta=access_token_expires
        )
        
        new_refresh_token = AuthService.create_refresh_token(user.id, db)
        
        # Revoke old refresh token
        db_token.is_revoked = True
        db.commit()
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Refresh token has expired")
    except jwt.JWTError:
        raise AuthenticationError("Invalid refresh token")
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/auth/logout", tags=["Authentication"])
async def logout(
    refresh_request: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Logout user by revoking refresh token"""
    try:
        db_token = db.query(RefreshToken).filter(
            RefreshToken.token == refresh_request.refresh_token,
            RefreshToken.user_id == current_user.id
        ).first()
        
        if db_token:
            db_token.is_revoked = True
            db.commit()
        
        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# User Management Routes
@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["User Management"])
async def create_user(
    user_create: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN]))
):
    """Create a new user (Admin only)"""
    try:
        user = UserService.create_user(db, user_create, created_by_admin=True)
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=[role.name for role in user.roles],
            created_at=user.created_at,
            last_login=user.last_login
        )
    except Exception as e:
        logger.error(f"User creation error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/users/me", response_model=UserResponse, tags=["User Management"])
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        roles=[role.name for role in current_user.roles],
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@app.put("/users/me/password", tags=["User Management"])
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    if not AuthService.verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    current_user.hashed_password = AuthService.get_password_hash(password_change.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Password changed successfully"}

@app.get("/users", response_model=List[UserResponse], tags=["User Management"])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.MANAGER]))
):
    """Get all users (Admin and Manager only)"""
    users = db.query(User).offset(skip).limit(limit).all()
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=[role.name for role in user.roles],
            created_at=user.created_at,
            last_login=user.last_login
        )
        for user in users
    ]

@app.get("/users/{user_id}", response_model=UserResponse, tags=["User Management"])
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN, RoleEnum.MANAGER]))
):
    """Get user by ID (Admin and Manager only)"""
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        is_active=user.is_active,
        is_verified=user.is_verified,
        roles=[role.name for role in user.roles],
        created_at=user.created_at,
        last_login=user.last_login
    )

@app.put("/users/{user_id}", response_model=UserResponse, tags=["User Management"])
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN]))
):
    """Update user (Admin only)"""
    try:
        user = UserService.update_user(db, user_id, user_update)
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=[role.name for role in user.roles],
            created_at=user.created_at,
            last_login=user.last_login
        )
    except Exception as e:
        logger.error(f"User update error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/users/{user_id}", tags=["User Management"])
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([RoleEnum.ADMIN]))
):
    """Delete user (Admin only)"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

# Protected routes with different access levels
@app.get("/admin/dashboard", tags=["Protected Routes"])
async def admin_dashboard(
    current_user: User = Depends(require_roles([RoleEnum.ADMIN]))
):
    """Admin dashboard (Admin only)"""
    return {
        "message": f"Welcome to admin dashboard, {current_user.username}!",
        "user_id": current_user.id,
        "user_roles": [role.name for role in current_user.roles],
        "access_level": "admin",
        "timestamp": datetime.utcnow()
    }

@app.get("/manager/dashboard", tags=["Protected Routes"])
async def manager_dashboard(
    current_user: User = Depends(require_roles([RoleEnum.MANAGER, RoleEnum.ADMIN]))
):
    """Manager dashboard (Manager and Admin access)"""
    return {
        "message": f"Welcome to manager dashboard, {current_user.username}!",
        "user_id": current_user.id,
        "user_roles": [role.name for role in current_user.roles],
        "access_level": "manager",
        "timestamp": datetime.utcnow()
    }

@app.get("/user/profile", tags=["Protected Routes"])
async def user_profile(current_user: User = Depends(get_current_user)):
    """User profile (All authenticated users)"""
    return {
        "message": f"Welcome to your profile, {current_user.username}!",
        "user_id": current_user.id,
        "user_roles": [role.name for role in current_user.roles],
        "access_level": "user",
        "last_login": current_user.last_login,
        "timestamp": datetime.utcnow()
    }

@app.get("/guest/info", tags=["Protected Routes"])
async def guest_info(
    current_user: User = Depends(require_roles([RoleEnum.GUEST, RoleEnum.USER, RoleEnum.MANAGER, RoleEnum.ADMIN]))
):
    """Guest information (All roles can access)"""
    return {
        "message": "Public information accessible to all authenticated users",
        "user_roles": [role.name for role in current_user.roles],
        "access_level": "guest",
        "timestamp": datetime.utcnow()
    }

# System routes
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/", tags=["System"])
async def root():
    """API root information"""
    return {
        "message": "OAuth API System",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "timestamp": datetime.utcnow()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
