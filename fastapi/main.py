from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from controllers import test_controller  # 필요에 따라 적절한 컨트롤러 경로로 수정하세요.
from superset import get_superset_data  # Superset API 호출 함수 임포트

import pkgutil
import importlib
import aiomysql

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



# MySQL 연결 설정 함수
async def get_db_connection():
    """MySQL 연결 설정 함수"""
    return await aiomysql.connect(
        host='opyter.iptime.org',
        user='bigdata_busan_3',        # MySQL 사용자 이름
        password='busan12345678*',    # MySQL 비밀번호
        db='web',                    # 데이터베이스 이름
        port=3306
    )



# employees 테이블의 데이터를 가져오는 엔드포인트 추가
@app.get("/user-management/user-list")
async def get_employees():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT employees.name, employees.employee_no, employees.position, employees.last_login FROM employees")
            result = await cursor.fetchall()
            conn.close()

            # 데이터 가공: 객체 배열로 변환
            employees = [
                {
                    "name": row[0],
                    "employeeNo": row[1],
                    "position": row[2],
                    "lastLogin": row[3]
                }
                for row in result
            ]

            return {"employees": employees}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# user_group 테이블의 데이터를 가져오는 엔드포인트 추가
@app.get("/user-management/user-groups")
async def get_user_groups():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM user_group")
            user_groups = await cursor.fetchall()
            conn.close()
            return {"user_groups": user_groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))