from fastapi import APIRouter, HTTPException
from typing import List

router = APIRouter()

# ============================================
# 소셜 관리 기본 엔드포인트
# ============================================

@router.get("/")
async def management_home():
    return {"message": "Welcome to Social Home"}

@router.get("/np-ratio/all")
async def np_ratio_all():
    return {"message": "NP ratio for all"}

@router.get("/np-ratio/car")
async def np_ratio_car():
    return {"message": "NP ratio for car"}

@router.get("/np-ratio/journal")
async def np_ratio_journal():
    return {"message": "NP ratio for journal"}

@router.get("/count/journal")
async def journal_count():
    return {"message": "Journal count"}

# ============================================
# 소셜 키워드 관련 엔드포인트
# ============================================

@router.get("/keywords")
async def get_keywords() -> List[str]:
    """키워드 데이터를 반환합니다."""
    return ["Electric Car", "Battery", "Energy", "Hybrid", "Sustainable"]
