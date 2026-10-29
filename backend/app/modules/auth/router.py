from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.auth import services
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import LoginRequest, TokenResponse, UsuarioOut

router = APIRouter(prefix="/auth", tags=["Autenticación"])

REFRESH_NO_VALIDO = "Refresh token inválido o expirado"


def _guardar_cookie_refresh(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path=settings.refresh_cookie_path,
    )


def _borrar_cookie_refresh(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.refresh_cookie_path,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        usuario = services.autenticar(db, payload.username, payload.password)
    except services.CredencialesInvalidasError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    access_token, refresh_token, expires_in = services.emitir_tokens(db, usuario)
    _guardar_cookie_refresh(response, refresh_token)

    return TokenResponse(accessToken=access_token, expiresIn=expires_in)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias=settings.REFRESH_COOKIE_NAME,
    ),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=REFRESH_NO_VALIDO,
        )

    try:
        access_token, nuevo_refresh, expires_in = services.refrescar_tokens(
            db, refresh_token
        )
    except services.RefreshInvalidoError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=REFRESH_NO_VALIDO,
        ) from exc

    _guardar_cookie_refresh(response, nuevo_refresh)

    return TokenResponse(accessToken=access_token, expiresIn=expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None,
        alias=settings.REFRESH_COOKIE_NAME,
    ),
    db: Session = Depends(get_db),
) -> None:
    if refresh_token:
        services.revocar_refresh(db, refresh_token)

    _borrar_cookie_refresh(response)


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_current_user)) -> Usuario:
    return usuario
