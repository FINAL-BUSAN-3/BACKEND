from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from controllers import test_controller  # 필요에 따라 적절한 컨트롤러 경로로 수정하세요.
from superset import get_superset_data  # Superset API 호출 함수 임포트

import pkgutil
import importlib

app = FastAPI()


# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def register_routers(app):
    """라우터를 자동으로 등록합니다."""
    router = APIRouter()
    package = "routers"
    for _, module_name, _ in pkgutil.iter_modules([package]):
        full_module_name = f"{package}.{module_name}"
        try:
            module = importlib.import_module(full_module_name)
            if hasattr(module, "router"):
                router.include_router(
                    module.router,
                    prefix=f"/{module_name.replace('_', '-')}",
                    tags=[module_name.capitalize()]
                )
                print(f"Registered router for {full_module_name}")
        except ImportError as e:
            print(f"Error importing {full_module_name}: {e}")

    app.include_router(router)

# 컨트롤러의 라우터를 애플리케이션에 포함
app.include_router(test_controller.router)

# 라우터 등록 실행
register_routers(app)

# 기존의 기능들 유지
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id, "name": f"Item {item_id}"}

# Superset 데이터 가져오는 엔드포인트
@app.get("/superset-data")
async def superset_data():
    try:
        data = await get_superset_data()  # Superset 데이터 호출
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))  # 에러 처리

# 새로운 /test 라우터 추가
@app.get("/test")
async def test_endpoint():
    return {"message": "Hello from FastAPI!"}
