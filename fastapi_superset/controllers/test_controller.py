from fastapi import APIRouter, HTTPException
from models.test_model import TestModel
from views.test_view import TestView
from superset import get_superset_data  # Superset API 호출 함수 임포트

router = APIRouter()

@router.get("/")
def read_root():
    # 모델에서 데이터를 가져옴
    data = TestModel.get_data()

    # 뷰를 통해 데이터를 포맷팅하여 반환
    return TestView.render(data)

@router.get("/superset-data")
async def superset_data():
    try:
        data = await get_superset_data()  # Superset 데이터 호출
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # 에러 처리
