from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse, RefreshTokenRequest
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ─── DEPENDENCY: ambil user dari JWT token ────────────────

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Dependency — dipakai di endpoint yang butuh autentikasi."""
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah kedaluwarsa",
            headers={"WWW-Authenticate": "Bearer"},
        )
    nim_nidn = payload.get("sub")
    user = auth_service.get_user_by_nim_nidn(db, nim_nidn)
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return user


# ─── POST /auth/login ─────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login dengan NIM (mahasiswa) atau NIDN (dosen).
    Return access token (24 jam) dan refresh token (7 hari).
    """
    user = auth_service.authenticate_user(db, request.nim_nidn, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="NIM/NIDN atau password salah"
        )

    token_data = {"sub": user.nim_nidn, "role": user.role.value}
    access_token  = auth_service.create_access_token(token_data)
    refresh_token = auth_service.create_refresh_token(token_data)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
    )


# ─── GET /auth/me ─────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def get_me(current_user = Depends(get_current_user)):
    """
    Ambil data user yang sedang login.
    Butuh header: Authorization: Bearer <token>
    """
    return current_user


# ─── POST /auth/refresh-token ─────────────────────────────

@router.post("/refresh-token", response_model=dict)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Perbarui access token menggunakan refresh token yang masih valid."""
    payload = auth_service.verify_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token tidak valid")

    token_data = {"sub": payload["sub"], "role": payload["role"]}
    new_access_token = auth_service.create_access_token(token_data)
    return {"access_token": new_access_token, "token_type": "bearer"}


# ─── POST /auth/logout ────────────────────────────────────

@router.post("/logout")
def logout(current_user = Depends(get_current_user)):
    """
    Logout — di sisi client token dihapus dari storage.
    Server-side invalidation bisa ditambahkan dengan Redis blacklist nanti.
    """
    return {"message": f"Sampai jumpa, {current_user.nama_lengkap}!"}