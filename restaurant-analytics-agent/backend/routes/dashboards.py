"""
Dashboard Routes
FastAPI router for dashboard and widget management endpoints
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from ..models.database_models import (
    DashboardCreate,
    DashboardUpdate,
    DashboardResponse,
    DashboardDetailResponse,
    WidgetCreate,
    WidgetUpdate,
    WidgetResponse,
    UserResponse,
)
from ..routes.auth import get_current_user_required
from ..services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboards", tags=["Dashboards"])


# ==================== Dashboard Management ====================

@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    dashboard_data: DashboardCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Create a new dashboard for the current user.
    
    Returns the created dashboard with widget count (0).
    """
    try:
        dashboard = await DashboardService.create_dashboard(
            user_id=current_user.id,
            name=dashboard_data.name,
            description=dashboard_data.description
        )
        return dashboard
    except Exception as e:
        logger.error(f"Error creating dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create dashboard"
        )


@router.get("", response_model=list[DashboardResponse])
async def list_dashboards(
    current_user: Annotated[UserResponse, Depends(get_current_user_required)],
    limit: int = 50,
    offset: int = 0
):
    """
    Get all dashboards for the current user.
    
    Returns a list of dashboards with widget counts, ordered by most recently updated.
    """
    from fastapi import Response
    
    try:
        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100"
            )
        
        if offset < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Offset must be non-negative"
            )
        
        dashboards = await DashboardService.get_user_dashboards(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        return dashboards
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing dashboards: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboards"
        )


@router.get("/{dashboard_id}", response_model=DashboardDetailResponse)
async def get_dashboard(
    dashboard_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Get detailed dashboard information with all widgets and their query data.
    
    Returns dashboard with widgets, or 404 if not found or unauthorized.
    """
    try:
        dashboard_uuid = UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format"
        )
    
    try:
        dashboard = await DashboardService.get_dashboard_detail(
            dashboard_id=dashboard_uuid,
            user_id=current_user.id
        )
        
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
        
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dashboard {dashboard_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch dashboard"
        )


@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: str,
    dashboard_data: DashboardUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Update dashboard name and/or description.
    
    Returns the updated dashboard or 404 if not found/unauthorized.
    """
    try:
        dashboard_uuid = UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format"
        )
    
    try:
        dashboard = await DashboardService.update_dashboard(
            dashboard_id=dashboard_uuid,
            user_id=current_user.id,
            name=dashboard_data.name,
            description=dashboard_data.description
        )
        
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
        
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dashboard {dashboard_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update dashboard"
        )


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Delete a dashboard and all its widgets.
    
    Returns 204 on success, 404 if not found/unauthorized.
    """
    try:
        dashboard_uuid = UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format"
        )
    
    try:
        deleted = await DashboardService.delete_dashboard(
            dashboard_id=dashboard_uuid,
            user_id=current_user.id
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dashboard {dashboard_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete dashboard"
        )


# ==================== Widget Management ====================

@router.post("/{dashboard_id}/widgets", response_model=WidgetResponse, status_code=status.HTTP_201_CREATED)
async def add_widget(
    dashboard_id: str,
    widget_data: WidgetCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Add a widget to a dashboard from query history.
    
    Returns the created widget with full query data, or 400 if widget limit exceeded.
    """
    try:
        dashboard_uuid = UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format"
        )
    
    # Validate size
    valid_sizes = ["small", "medium", "large", "full"]
    if widget_data.size not in valid_sizes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Size must be one of: {', '.join(valid_sizes)}"
        )
    
    try:
        widget = await DashboardService.add_widget(
            dashboard_id=dashboard_uuid,
            user_id=current_user.id,
            query_id=widget_data.query_id,
            position=widget_data.position,
            size=widget_data.size
        )
        
        if not widget:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create widget"
            )
        
        return widget
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding widget to dashboard {dashboard_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add widget"
        )


@router.put("/{dashboard_id}/widgets/{widget_id}", response_model=WidgetResponse)
async def update_widget(
    dashboard_id: str,
    widget_id: str,
    widget_data: WidgetUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Update widget position and/or size.
    
    Returns the updated widget with query data, or 404 if not found/unauthorized.
    """
    try:
        dashboard_uuid = UUID(dashboard_id)
        widget_uuid = UUID(widget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard or widget ID format"
        )
    
    # Validate size if provided
    if widget_data.size is not None:
        valid_sizes = ["small", "medium", "large", "full"]
        if widget_data.size not in valid_sizes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Size must be one of: {', '.join(valid_sizes)}"
            )
    
    try:
        widget = await DashboardService.update_widget(
            widget_id=widget_uuid,
            dashboard_id=dashboard_uuid,
            user_id=current_user.id,
            position=widget_data.position,
            size=widget_data.size
        )
        
        if not widget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget not found"
            )
        
        return widget
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating widget {widget_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update widget"
        )


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    dashboard_id: str,
    widget_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Remove a widget from a dashboard.
    
    Returns 204 on success, 404 if not found/unauthorized.
    """
    try:
        dashboard_uuid = UUID(dashboard_id)
        widget_uuid = UUID(widget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard or widget ID format"
        )
    
    try:
        deleted = await DashboardService.delete_widget(
            widget_id=widget_uuid,
            dashboard_id=dashboard_uuid,
            user_id=current_user.id
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Widget not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting widget {widget_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete widget"
        )


@router.post("/{dashboard_id}/refresh", response_model=DashboardDetailResponse)
async def refresh_dashboard(
    dashboard_id: str,
    current_user: Annotated[UserResponse, Depends(get_current_user_required)]
):
    """
    Refresh dashboard data by re-fetching all widget query data.
    
    This endpoint simply returns the current dashboard state. With static data,
    results don't change, but this mimics a refresh for when dynamic data is added.
    """
    try:
        dashboard_uuid = UUID(dashboard_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid dashboard ID format"
        )
    
    try:
        dashboard = await DashboardService.get_dashboard_detail(
            dashboard_id=dashboard_uuid,
            user_id=current_user.id
        )
        
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found"
            )
        
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing dashboard {dashboard_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh dashboard"
        )
