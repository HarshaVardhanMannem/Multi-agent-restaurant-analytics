"""
Authentication Routes
FastAPI router for user authentication endpoints
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, status

from ..models.database_models import (
    QueryHistoryResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from ..services.auth_service import AuthService, QueryHistoryService
from ..utils.auth import create_access_token, get_user_id_from_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


# ==================== Dependency for getting current user ====================


async def get_current_user_optional(
    authorization: Annotated[str | None, Header()] = None
) -> UserResponse | None:
    """
    Optional authentication dependency.
    Returns user if valid token provided, None otherwise.
    Does not raise errors - allows unauthenticated access.
    """
    if not authorization:
        return None
    
    # Extract token from "Bearer <token>" format
    if not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    user_id = get_user_id_from_token(token)
    if not user_id:
        return None
    
    return await AuthService.get_user_by_id(user_id)


async def get_current_user_required(
    authorization: Annotated[str | None, Header()] = None
) -> UserResponse:
    """
    Required authentication dependency.
    Returns user if valid token provided, raises 401 otherwise.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization[7:]
    user_id = get_user_id_from_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await AuthService.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# ==================== Auth Endpoints ====================


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user account.
    
    Returns a JWT token upon successful registration.
    """
    try:
        user = await AuthService.create_user(user_data)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create access token
        access_token, expires_in = create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        logger.info(f"User registered: {user.email}")
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    Authenticate user and return JWT token.
    """
    try:
        user = await AuthService.authenticate_user(
            credentials.email,
            credentials.password
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Login error: {error_msg}")
        
        # Check if it's a database/table error
        if "does not exist" in error_msg.lower() or "relation" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database tables not initialized. Please register a new account first.",
            )
        elif "connection" in error_msg.lower() or "network" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable. Please try again later.",
            )
        else:
            # Generic database error
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database error. Please try again later.",
            )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token, expires_in = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    logger.info(f"User logged in: {user.email}")
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Get current authenticated user information.
    """
    return current_user


@router.get("/history", response_model=list[QueryHistoryResponse])
async def get_query_history(
    current_user: Annotated[UserResponse, Depends(get_current_user_required)],
    limit: int = 50,
    offset: int = 0
):
    """
    Get query history for the current user.
    """
    return await QueryHistoryService.get_user_queries(
        current_user.id,
        limit=min(limit, 100),  # Cap at 100
        offset=offset
    )


@router.get("/history/widgets")
async def get_query_history_for_widgets(
    current_user: Annotated[UserResponse, Depends(get_current_user_required)],
    limit: int = 20
):
    """
    Get query history with full results for restoring widgets.
    Returns detailed data including results_sample, columns, and visualization_config.
    """
    return await QueryHistoryService.get_user_queries_with_results(
        current_user.id,
        limit=min(limit, 50)  # Cap at 50 for performance
    )


@router.get("/history/{query_id}")
async def get_query_detail(
    query_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Get detailed information about a specific query.
    """
    query = await QueryHistoryService.get_query_by_id(query_id)
    
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found"
        )
    
    # Check if user owns this query (or is admin)
    if query.user_id and query.user_id != current_user.id:
        from ..models.database_models import UserRole
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
    
    return query


@router.delete("/history/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_query(
    query_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Delete a query from history.
    """
    deleted = await QueryHistoryService.delete_query(query_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Query not found or access denied"
        )
    
    return None