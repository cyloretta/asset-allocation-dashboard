"""
用户配置 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import logging

from database import (
    async_session,
    create_user_config, get_user_config, get_user_config_by_name,
    list_user_configs, update_user_config, delete_user_config
)
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/config", tags=["config"])


# ============================================
# Pydantic Models
# ============================================

class AssetConstraint(BaseModel):
    min: float = Field(0.0, ge=0, le=1)
    max: float = Field(0.4, ge=0, le=1)


class UserConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    asset_pool: List[str] = Field(default_factory=list)
    asset_constraints: Optional[Dict[str, AssetConstraint]] = None
    max_drawdown: float = Field(0.25, ge=0.05, le=0.5)
    target_sharpe: float = Field(1.0, ge=0.5, le=3.0)
    rebalance_threshold: float = Field(0.05, ge=0.01, le=0.2)
    preferred_method: str = Field("composite")
    use_ai_adjustments: bool = True


class UserConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    asset_pool: Optional[List[str]] = None
    asset_constraints: Optional[Dict[str, AssetConstraint]] = None
    max_drawdown: Optional[float] = Field(None, ge=0.05, le=0.5)
    target_sharpe: Optional[float] = Field(None, ge=0.5, le=3.0)
    rebalance_threshold: Optional[float] = Field(None, ge=0.01, le=0.2)
    preferred_method: Optional[str] = None
    use_ai_adjustments: Optional[bool] = None


class UserConfigResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    asset_pool: List[str]
    asset_constraints: Optional[Dict]
    max_drawdown: float
    target_sharpe: float
    rebalance_threshold: float
    preferred_method: str
    use_ai_adjustments: bool
    created_at: str
    updated_at: Optional[str]


# ============================================
# API Endpoints
# ============================================

@router.get("/")
async def list_configs():
    """列出所有用户配置"""
    async with async_session() as session:
        configs = await list_user_configs(session)
        return {
            "data": [
                {
                    "id": c.id,
                    "name": c.name,
                    "is_active": bool(c.is_active),
                    "asset_pool": c.asset_pool or [],
                    "asset_constraints": c.asset_constraints,
                    "max_drawdown": c.max_drawdown,
                    "target_sharpe": c.target_sharpe,
                    "rebalance_threshold": c.rebalance_threshold,
                    "preferred_method": c.preferred_method,
                    "use_ai_adjustments": bool(c.use_ai_adjustments),
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None
                }
                for c in configs
            ]
        }


@router.get("/available-assets")
async def get_available_assets():
    """获取可用资产列表"""
    return {
        "data": {
            asset: {
                "name": info.get("name", asset),
                "min_weight": info.get("min_weight", 0),
                "max_weight": info.get("max_weight", 0.4)
            }
            for asset, info in settings.assets.items()
        }
    }


@router.get("/{config_id}")
async def get_config(config_id: int):
    """获取单个配置"""
    async with async_session() as session:
        config = await get_user_config(session, config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")

        return {
            "data": {
                "id": config.id,
                "name": config.name,
                "is_active": bool(config.is_active),
                "asset_pool": config.asset_pool or [],
                "asset_constraints": config.asset_constraints,
                "max_drawdown": config.max_drawdown,
                "target_sharpe": config.target_sharpe,
                "rebalance_threshold": config.rebalance_threshold,
                "preferred_method": config.preferred_method,
                "use_ai_adjustments": bool(config.use_ai_adjustments),
                "created_at": config.created_at.isoformat() if config.created_at else None,
                "updated_at": config.updated_at.isoformat() if config.updated_at else None
            }
        }


@router.post("/")
async def create_config(request: UserConfigCreate):
    """创建配置"""
    # 验证 asset_pool 中的资产
    valid_assets = set(settings.assets.keys())
    invalid = [a for a in request.asset_pool if a not in valid_assets]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"无效的资产: {', '.join(invalid)}。可用资产: {', '.join(valid_assets)}"
        )

    # 验证优化方法
    valid_methods = ["max_sharpe", "min_volatility", "risk_parity", "composite", "risk_aware", "max_sharpe_cvar"]
    if request.preferred_method not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"无效的优化方法。可用: {', '.join(valid_methods)}"
        )

    async with async_session() as session:
        # 检查名称是否已存在
        existing = await get_user_config_by_name(session, request.name)
        if existing:
            raise HTTPException(status_code=400, detail="配置名称已存在")

        # 转换 asset_constraints
        constraints = None
        if request.asset_constraints:
            constraints = {k: {"min": v.min, "max": v.max} for k, v in request.asset_constraints.items()}

        config = await create_user_config(
            session,
            name=request.name,
            asset_pool=request.asset_pool or list(valid_assets),
            asset_constraints=constraints,
            max_drawdown=request.max_drawdown,
            target_sharpe=request.target_sharpe,
            rebalance_threshold=request.rebalance_threshold,
            preferred_method=request.preferred_method,
            use_ai_adjustments=request.use_ai_adjustments
        )

        logger.info(f"Created user config: {config.name} (id={config.id})")

        return {
            "data": {
                "id": config.id,
                "name": config.name,
                "message": "配置创建成功"
            }
        }


@router.put("/{config_id}")
async def update_config_endpoint(config_id: int, request: UserConfigUpdate):
    """更新配置"""
    # 验证 asset_pool 中的资产
    if request.asset_pool:
        valid_assets = set(settings.assets.keys())
        invalid = [a for a in request.asset_pool if a not in valid_assets]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"无效的资产: {', '.join(invalid)}"
            )

    # 验证优化方法
    if request.preferred_method:
        valid_methods = ["max_sharpe", "min_volatility", "risk_parity", "composite", "risk_aware", "max_sharpe_cvar"]
        if request.preferred_method not in valid_methods:
            raise HTTPException(
                status_code=400,
                detail=f"无效的优化方法"
            )

    async with async_session() as session:
        # 转换更新数据
        update_data = {}
        if request.name is not None:
            update_data['name'] = request.name
        if request.asset_pool is not None:
            update_data['asset_pool'] = request.asset_pool
        if request.asset_constraints is not None:
            update_data['asset_constraints'] = {
                k: {"min": v.min, "max": v.max}
                for k, v in request.asset_constraints.items()
            }
        if request.max_drawdown is not None:
            update_data['max_drawdown'] = request.max_drawdown
        if request.target_sharpe is not None:
            update_data['target_sharpe'] = request.target_sharpe
        if request.rebalance_threshold is not None:
            update_data['rebalance_threshold'] = request.rebalance_threshold
        if request.preferred_method is not None:
            update_data['preferred_method'] = request.preferred_method
        if request.use_ai_adjustments is not None:
            update_data['use_ai_adjustments'] = request.use_ai_adjustments

        config = await update_user_config(session, config_id, **update_data)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")

        logger.info(f"Updated user config: {config.name} (id={config.id})")

        return {"data": {"id": config.id, "message": "配置更新成功"}}


@router.delete("/{config_id}")
async def delete_config_endpoint(config_id: int):
    """删除配置（软删除）"""
    async with async_session() as session:
        success = await delete_user_config(session, config_id)
        if not success:
            raise HTTPException(status_code=404, detail="配置不存在")

        logger.info(f"Deleted user config: id={config_id}")
        return {"data": {"message": "配置已删除"}}
