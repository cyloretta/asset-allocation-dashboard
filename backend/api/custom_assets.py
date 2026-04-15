"""
自定义资产管理 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from database import (
    async_session,
    create_custom_asset, get_custom_asset, list_custom_assets,
    update_custom_asset, delete_custom_asset
)
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/assets", tags=["assets"])


# ============================================
# Pydantic Models
# ============================================

VALID_ASSET_TYPES = ["us_equity", "crypto", "commodity", "bond", "etf", "cash", "international"]

class AssetCreate(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20, description="资产代码")
    name: str = Field(..., min_length=1, max_length=100, description="资产名称")
    asset_type: str = Field(..., description="资产类型")
    min_weight: float = Field(0.0, ge=0, le=1, description="最小权重")
    max_weight: float = Field(0.4, ge=0, le=1, description="最大权重")


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    asset_type: Optional[str] = None
    min_weight: Optional[float] = Field(None, ge=0, le=1)
    max_weight: Optional[float] = Field(None, ge=0, le=1)


class AssetResponse(BaseModel):
    ticker: str
    name: str
    asset_type: str
    min_weight: float
    max_weight: float
    is_builtin: bool = False


# ============================================
# API Endpoints
# ============================================

@router.get("/")
async def list_assets():
    """
    获取所有可用资产（内置 + 自定义）
    """
    # 内置资产
    builtin = {
        ticker: {
            "ticker": ticker,
            "name": info.get("name", ticker),
            "asset_type": info.get("type", "unknown"),
            "min_weight": info.get("min_weight", 0),
            "max_weight": info.get("max_weight", 0.4),
            "is_builtin": True
        }
        for ticker, info in settings.assets.items()
    }

    # 自定义资产
    async with async_session() as session:
        custom = await list_custom_assets(session)
        for asset in custom:
            if asset.ticker not in builtin:  # 避免覆盖内置
                builtin[asset.ticker] = {
                    "ticker": asset.ticker,
                    "name": asset.name,
                    "asset_type": asset.asset_type,
                    "min_weight": asset.min_weight,
                    "max_weight": asset.max_weight,
                    "is_builtin": False
                }

    return {
        "data": list(builtin.values()),
        "builtin_count": len(settings.assets),
        "custom_count": len(builtin) - len(settings.assets)
    }


@router.get("/types")
async def get_asset_types():
    """获取资产类型列表"""
    return {
        "data": [
            {"value": "us_equity", "label": "美股", "description": "美国股票和ETF"},
            {"value": "international", "label": "国际", "description": "非美国市场"},
            {"value": "crypto", "label": "加密货币", "description": "比特币、以太坊等"},
            {"value": "commodity", "label": "商品", "description": "黄金、原油等"},
            {"value": "bond", "label": "债券", "description": "国债、公司债等"},
            {"value": "etf", "label": "ETF", "description": "交易所交易基金"},
            {"value": "cash", "label": "现金", "description": "货币市场"}
        ]
    }


@router.post("/")
async def add_asset(request: AssetCreate):
    """
    添加自定义资产
    """
    ticker = request.ticker.upper()

    # 检查是否已存在于内置资产
    if ticker in settings.assets:
        raise HTTPException(
            status_code=400,
            detail=f"'{ticker}' 是内置资产，无法重复添加"
        )

    # 验证资产类型
    if request.asset_type not in VALID_ASSET_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的资产类型。可选: {', '.join(VALID_ASSET_TYPES)}"
        )

    # 验证权重
    if request.min_weight > request.max_weight:
        raise HTTPException(
            status_code=400,
            detail="最小权重不能大于最大权重"
        )

    async with async_session() as session:
        # 检查是否已存在
        existing = await get_custom_asset(session, ticker)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"资产 '{ticker}' 已存在"
            )

        asset = await create_custom_asset(
            session,
            ticker=ticker,
            name=request.name,
            asset_type=request.asset_type,
            min_weight=request.min_weight,
            max_weight=request.max_weight
        )

        logger.info(f"Added custom asset: {ticker}")

        return {
            "data": {
                "ticker": asset.ticker,
                "name": asset.name,
                "asset_type": asset.asset_type,
                "message": f"资产 '{ticker}' 添加成功"
            }
        }


@router.put("/{ticker}")
async def update_asset_endpoint(ticker: str, request: AssetUpdate):
    """
    更新自定义资产
    """
    ticker = ticker.upper()

    # 不允许修改内置资产
    if ticker in settings.assets:
        raise HTTPException(
            status_code=400,
            detail=f"'{ticker}' 是内置资产，无法修改"
        )

    # 验证资产类型
    if request.asset_type and request.asset_type not in VALID_ASSET_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"无效的资产类型"
        )

    async with async_session() as session:
        update_data = {}
        if request.name is not None:
            update_data['name'] = request.name
        if request.asset_type is not None:
            update_data['asset_type'] = request.asset_type
        if request.min_weight is not None:
            update_data['min_weight'] = request.min_weight
        if request.max_weight is not None:
            update_data['max_weight'] = request.max_weight

        asset = await update_custom_asset(session, ticker, **update_data)
        if not asset:
            raise HTTPException(status_code=404, detail=f"资产 '{ticker}' 不存在")

        logger.info(f"Updated custom asset: {ticker}")

        return {"data": {"ticker": ticker, "message": "资产更新成功"}}


@router.delete("/{ticker}")
async def remove_asset(ticker: str):
    """
    删除自定义资产
    """
    ticker = ticker.upper()

    # 不允许删除内置资产
    if ticker in settings.assets:
        raise HTTPException(
            status_code=400,
            detail=f"'{ticker}' 是内置资产，无法删除"
        )

    async with async_session() as session:
        success = await delete_custom_asset(session, ticker)
        if not success:
            raise HTTPException(status_code=404, detail=f"资产 '{ticker}' 不存在")

        logger.info(f"Deleted custom asset: {ticker}")
        return {"data": {"message": f"资产 '{ticker}' 已删除"}}


@router.get("/search/{query}")
async def search_assets(query: str):
    """
    搜索资产（验证资产代码是否有效）

    TODO: 集成真实的资产搜索API（如 Yahoo Finance 搜索）
    """
    query = query.upper()

    # 常用资产映射
    COMMON_ASSETS = {
        # 美股 ETF
        "VOO": {"name": "Vanguard S&P 500 ETF", "type": "etf"},
        "VTI": {"name": "Vanguard Total Stock Market ETF", "type": "etf"},
        "IWM": {"name": "iShares Russell 2000 ETF", "type": "etf"},
        "EFA": {"name": "iShares MSCI EAFE ETF", "type": "international"},
        "EEM": {"name": "iShares MSCI Emerging Markets ETF", "type": "international"},
        "VWO": {"name": "Vanguard Emerging Markets ETF", "type": "international"},
        "ARKK": {"name": "ARK Innovation ETF", "type": "etf"},
        "XLF": {"name": "Financial Select Sector SPDR", "type": "etf"},
        "XLK": {"name": "Technology Select Sector SPDR", "type": "etf"},
        "XLE": {"name": "Energy Select Sector SPDR", "type": "etf"},
        # 债券
        "BND": {"name": "Vanguard Total Bond Market ETF", "type": "bond"},
        "AGG": {"name": "iShares Core US Aggregate Bond ETF", "type": "bond"},
        "LQD": {"name": "iShares iBoxx Investment Grade Corporate Bond ETF", "type": "bond"},
        "HYG": {"name": "iShares iBoxx High Yield Corporate Bond ETF", "type": "bond"},
        "TIP": {"name": "iShares TIPS Bond ETF", "type": "bond"},
        "SHY": {"name": "iShares 1-3 Year Treasury Bond ETF", "type": "bond"},
        "IEF": {"name": "iShares 7-10 Year Treasury Bond ETF", "type": "bond"},
        # 商品
        "SLV": {"name": "iShares Silver Trust", "type": "commodity"},
        "USO": {"name": "United States Oil Fund", "type": "commodity"},
        "DBA": {"name": "Invesco DB Agriculture Fund", "type": "commodity"},
        # 加密货币
        "ETH-USD": {"name": "Ethereum", "type": "crypto"},
        "SOL-USD": {"name": "Solana", "type": "crypto"},
        "BNB-USD": {"name": "Binance Coin", "type": "crypto"},
        "ADA-USD": {"name": "Cardano", "type": "crypto"},
        "XRP-USD": {"name": "Ripple", "type": "crypto"},
        "DOGE-USD": {"name": "Dogecoin", "type": "crypto"},
        # 科技股
        "AAPL": {"name": "Apple Inc.", "type": "us_equity"},
        "MSFT": {"name": "Microsoft Corporation", "type": "us_equity"},
        "GOOGL": {"name": "Alphabet Inc.", "type": "us_equity"},
        "AMZN": {"name": "Amazon.com Inc.", "type": "us_equity"},
        "NVDA": {"name": "NVIDIA Corporation", "type": "us_equity"},
        "META": {"name": "Meta Platforms Inc.", "type": "us_equity"},
        "TSLA": {"name": "Tesla Inc.", "type": "us_equity"},
    }

    # 检查是否在常用资产中
    if query in COMMON_ASSETS:
        info = COMMON_ASSETS[query]
        return {
            "data": {
                "ticker": query,
                "name": info["name"],
                "asset_type": info["type"],
                "found": True
            }
        }

    # 检查是否已在系统中
    if query in settings.assets:
        info = settings.assets[query]
        return {
            "data": {
                "ticker": query,
                "name": info.get("name", query),
                "asset_type": info.get("type", "unknown"),
                "found": True,
                "is_builtin": True
            }
        }

    # 模糊搜索
    matches = []
    for ticker, info in COMMON_ASSETS.items():
        if query in ticker or query.lower() in info["name"].lower():
            matches.append({
                "ticker": ticker,
                "name": info["name"],
                "asset_type": info["type"]
            })

    if matches:
        return {
            "data": {
                "found": False,
                "suggestions": matches[:5]
            }
        }

    return {
        "data": {
            "found": False,
            "message": f"未找到 '{query}'，您可以手动添加"
        }
    }
