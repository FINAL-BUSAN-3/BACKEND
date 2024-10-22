from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from controllers import test_controller  # 필요에 따라 적절한 컨트롤러 경로로 수정하세요.
from superset import get_superset_data  # Superset API 호출 함수 임포트

import pkgutil
import importlib
import aiomysql
from pydantic import BaseModel  # BaseModel 임포트 추가

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
@app.get("/user-management/group-list")
async def get_user_groups():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM user_groups")
            user_groups = await cursor.fetchall()
            conn.close()
            return {"user_groups": user_groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


############ 주가 데이터 ###############
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# app = FastAPI()
stock_data = []

def get_naver_stock_price(symbol: str):
    try:
        url = f"https://finance.naver.com/item/main.nhn?code={symbol}"
        response = requests.get(url)
        response.raise_for_status()  # HTTP 오류 체크
        soup = BeautifulSoup(response.text, 'html.parser')
        price_element = soup.select_one('.no_today .blind')
        if price_element is None:
            raise ValueError("주가 정보를 찾을 수 없습니다.")
        price = price_element.text
        return price
    except Exception as e:
        print(f"Error fetching stock price: {e}")
        return None

@app.get("/stock-history/{symbol}")
async def fetch_stock_history(symbol: str):
    global stock_data
    price = get_naver_stock_price(symbol)
    if price:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 중복 데이터 방지: 마지막으로 저장된 가격과 시간이 같은 경우 추가하지 않음
        if not stock_data or stock_data[-1]["price"] != float(price.replace(",", "")):
            stock_data.append({"time": timestamp, "price": float(price.replace(",", ""))})
        # 오래된 데이터 제거: 마지막 100개의 데이터만 유지
        if len(stock_data) > 100:
            stock_data = stock_data[-100:]
    return stock_data[-10:]  # 마지막 10개 데이터만 반환

###############사용자, 권한 추가##############
# 사용자 데이터 추가를 위한 Pydantic 모델
class User(BaseModel):
    name: str
    employeeNo: int
    password: str
    role: str

# 권한 데이터 추가를 위한 Pydantic 모델
class Group(BaseModel):
    groupName: str
    groupDescription: str

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MySQL 연결 설정 함수
async def get_db_connection():
    """MySQL 연결 설정 함수"""
    return await aiomysql.connect(
        host='opyter.iptime.org',
        user='bigdata_busan_3',
        password='busan12345678*',
        db='web',
        port=3306
    )

# 사용자 추가 엔드포인트
@app.post("/user-management/user-add")
async def add_user(user: User):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO employees (name, employee_no, position) VALUES (%s, %s, %s)",
                (user.name, user.employeeNo, user.role)
            )
            await conn.commit()
            conn.close()
            return {"message": "사용자가 성공적으로 추가되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 권한 추가 엔드포인트
@app.post("/user-management/group-add")
async def add_group(group: Group):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO user_groups (group_name, description) VALUES (%s, %s)",
                (group.groupName, group.groupDescription)
            )
            await conn.commit()
            conn.close()
            return {"message": "권한이 성공적으로 추가되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

########### 삭제 #############
# 사용자 삭제 엔드포인트
@app.delete("/user-management/user-delete/{employee_no}")
async def delete_user(employee_no: int):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM employees WHERE employee_no = %s", (employee_no,))
            await conn.commit()
            conn.close()
            return {"message": "사용자가 성공적으로 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 권한 삭제 엔드포인트
@app.delete("/user-management/group-delete/{group_name}")
async def delete_group(group_name: str):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM user_groups WHERE group_name = %s", (group_name,))
            await conn.commit()
            conn.close()
            return {"message": "권한이 성공적으로 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# models 테이블의 데이터를 가져오는 엔드포인트 추가
@app.get("/model-deployment/model-select")
async def get_model_file_names():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT model_file_name FROM models")
            result = await cursor.fetchall()
            conn.close()

            # 데이터 가공: 모델 파일 이름 목록 생성
            model_file_names = [row[0] for row in result] if result else []

            return {"model_file_names": model_file_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


