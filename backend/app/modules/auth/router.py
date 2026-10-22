from sys import stderr
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import UsuarioLogin, Token
from sqlalchemy import select


router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=Token)
def login(credentials: UsuarioLogin, db: Session = Depends(get_db)):
    """Autentica usuario y retorna token JWT."""
    print(f"LOGIN ATTEMPT: {credentials.username}", file=stderr, flush=True)
    try:
        stmt = select(Usuario).where(Usuario.username == credentials.username)
        user = db.execute(stmt).scalar_one_or_none()
        print(f"USER FOUND: {user is not None}", file=stderr, flush=True)
        
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.activo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuario inactivo"
            )
        
        print(f"Creating token for user: {user.id}", file=stderr, flush=True)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        print(f"Token created: {access_token[:20]}...", file=stderr, flush=True)
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        # Log to file
        with open("login_error.log", "a") as f:
            f.write(f"\n--- LOGIN ERROR ---\n")
            f.write(f"Error: {type(e).__name__}: {e}\n")
            traceback.print_exc(file=f)
        print(f"LOGIN ERROR: {type(e).__name__}: {e}", file=stderr, flush=True)
        # Re-raise the original exception to see the traceback
        raise


@router.post("/register", response_model=Token)
def register(credentials: UsuarioLogin, db: Session = Depends(get_db)):
    """Registra un nuevo usuario (solo para desarrollo)."""
    # Verificar si existe
    stmt = select(Usuario).where(Usuario.username == credentials.username)
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario ya existe"
        )
    
    user = Usuario(
        username=credentials.username,
        email=f"{credentials.username}@cafedefinca.com",
        hashed_password=get_password_hash(credentials.password),
        rol="operador",
        activo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}