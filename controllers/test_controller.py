# controllers/base_controller.py
from fastapi import APIRouter
from models.test_model import TestModel
from views.test_view import TestView

router = APIRouter()


@router.get("/")
def read_root():
    # 모델에서 데이터를 가져옴
    data = TestModel.get_data()

    # 뷰를 통해 데이터를 포맷팅하여 반환
    return TestView.render(data)