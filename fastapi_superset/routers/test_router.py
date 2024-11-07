from fastapi import APIRouter
from superset import get_superset_data  # Superset API 호출 함수
from fastapi import HTTPException

router = APIRouter()  # APIRouter 인스턴스 생성

@router.get("/superset-data")  # 라우터 엔드포인트 정의
async def superset_data():
    try:
        data = await get_superset_data()  # Superset 데이터 호출
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # 에러 처리
