from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends #로그인
from controllers import test_controller  #필요에 따라 적절한 컨트롤러 경로로 수정하세요.
from superset import get_superset_data  #Superset API 호출 함수 임포트
from datetime import datetime, timedelta

import pkgutil
import importlib
import aiomysql
from pydantic import BaseModel  # BaseModel 임포트 추가
from typing import List
import logging
import pytz

#비밀번호 암호화를 위한 라이브러리
from passlib.context import CryptContext
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# 로깅 설정 추가
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
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
                print(f"Registered router for {full_module_name}")  # 경로 등록 확인
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

#######################3######### user list #################################33#######
# employees 테이블의 데이터를 가져오는 엔드포인트
@app.get("/user-management/user-list")
async def get_employees():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT employees.name, employees.employee_no, employees.position, employees.last_login FROM employees"
            )
            result = await cursor.fetchall()
            conn.close()

            # last_login이 None이면 "최근 기록이 없음"으로 설정하고, 날짜가 있으면 한국 시간대로 변환하여 ISO 문자열로 반환
            kst = pytz.timezone("Asia/Seoul")
            employees = [
                {
                    "id": row[1],  # employee_no를 고유 ID로 사용
                    "name": row[0],
                    "employeeNo": row[1],
                    "position": row[2],
                    "lastLogin": row[3].astimezone(kst).isoformat() if row[3] else "최근 기록이 없음"
                }
                for row in result
            ]

            return {"employees": employees}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#################################### group list ######################################
@app.get("/user-management/group-list")
async def get_user_groups():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT id, group_name, description FROM user_groups")
            user_groups = await cursor.fetchall()
        conn.close()
        return {"user_groups": user_groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


################################ 사용자, 권한 추가 #######################################
# 사용자 데이터 추가를 위한 Pydantic 모델
class User(BaseModel):
    name: str
    employeeNo: int
    position: str

# 권한 데이터 추가를 위한 Pydantic 모델
class Group(BaseModel):
    group_name: str
    description: str

@app.post("/user-management/user-add")
async def add_user(user: User):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            # 동일한 employeeNo가 있는지 확인
            await cursor.execute(
                "SELECT COUNT(*) FROM employees WHERE employee_no = %s", (user.employeeNo,)
            )
            (count_employee,) = await cursor.fetchone()

            # 동일한 name이 있는지 확인
            await cursor.execute(
                "SELECT COUNT(*) FROM employees WHERE name = %s", (user.name,)
            )
            (count_name,) = await cursor.fetchone()

            if count_employee > 0:
                raise HTTPException(status_code=400, detail="이미 존재하는 사번입니다.")

            if count_name > 0:
                raise HTTPException(status_code=400, detail="이미 존재하는 이름입니다.")

            # 중복되지 않은 경우에만 추가
            await cursor.execute(
                "INSERT INTO employees (name, employee_no, position, last_login) VALUES (%s, %s, %s, NULL)",
                (user.name, user.employeeNo, user.position)  # last_login을 NULL로 설정
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
                (group.group_name, group.description)  # 수정: groupName -> group_name, groupDescription -> description
            )
            await conn.commit()
            conn.close()
            return {"message": "권한이 성공적으로 추가되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

########################################## 사용자, 권한 삭제 #################################################
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
@app.delete("/user-management/group-delete/{group_id}")
async def delete_group(group_id: int):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM user_groups WHERE id = %s", (group_id,))
            await conn.commit()
            conn.close()
            return {"message": "권한이 성공적으로 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


####################################### 사용자 상세정보 #######################################
# 사용자 정보 업데이트 엔드포인트 추가
class UpdateUser(BaseModel):
    id: int
    position: str  # 사용자의 단일 권한을 처리하기 위해 position 필드 사용

# 사용자 정보 업데이트 엔드포인트 수정
@app.put("/user-management/user-detail/{user_id}")
async def update_user_detail(user_id: int, user: UpdateUser):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            # 사용자의 직위(position) 업데이트
            await cursor.execute(
                "UPDATE employees SET position = %s WHERE employee_no = %s",
                (user.position, user_id)
            )
            await conn.commit()
            conn.close()
            return {"message": "사용자 정보가 성공적으로 업데이트되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 상세 정보를 가져오는 엔드포인트 수정
@app.get("/user-management/user-detail/{user_id}")
async def get_user_detail(user_id: int):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT name, employee_no, position, last_login FROM employees WHERE employee_no = %s", (user_id,)
            )
            user_result = await cursor.fetchone()

            if not user_result:
                raise HTTPException(status_code=404, detail="User not found")

            # 권한을 ';'로 나눠 리스트로 반환
            user = {
                "name": user_result[0],
                "employeeNo": user_result[1],
                "position": user_result[2],
                "lastLogin": user_result[3],
                "roles": user_result[2].split(';') if user_result[2] else []
            }

            conn.close()
            return user
    except Exception as e:
        print(f"Error fetching user detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

########################################## 모델 ###########################################
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


########################################## 주가 데이터 ##########################################
import requests
from bs4 import BeautifulSoup
from datetime import datetime

stock_data_map = {
    "005380": [],  # 현대차 주가 데이터
    "000270": []   # 기아차 주가 데이터
}
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
    global stock_data_map
    price = get_naver_stock_price(symbol)
    if price:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        current_price = float(price.replace(",", ""))

        # 이전 데이터와 가격 및 시간을 비교하여 동일할 경우 추가하지 않음
        if stock_data_map[symbol] and stock_data_map[symbol][-1]["price"] == current_price:
            return stock_data_map[symbol][-10:]  # 마지막 10개 데이터만 반환

        # 주가 변동 여부와 관계없이 데이터 추가
        stock_data_map[symbol].append({"time": timestamp, "price": current_price})

        # 오래된 데이터 제거: 마지막 100개의 데이터만 유지
        if len(stock_data_map[symbol]) > 100:
            stock_data_map[symbol] = stock_data_map[symbol][-100:]

    return stock_data_map[symbol][-10:]  # 마지막 10개 데이터만 반환


############################### HD_sales와 KIA_sales 데이터 엔드포인트 ##################################
class SalesData(BaseModel):
    year: str
    count: int

@app.get("/sales/hd", response_model=List[SalesData])
async def get_hd_sales():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT year, count FROM HD_sales ORDER BY year ASC")
            result = await cursor.fetchall()
            conn.close()

            hd_sales = [{"year": row[0], "count": row[1]} for row in result]
            return hd_sales
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sales/kia", response_model=List[SalesData])
async def get_kia_sales():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT year, count FROM KIA_sales ORDER BY year ASC")
            result = await cursor.fetchall()
            conn.close()

            kia_sales = [{"year": row[0], "count": row[1]} for row in result]
            return kia_sales
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


######################################## 로그인 ############################################
# 비밀번호 암호화를 위한 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 데이터베이스 설정 (예: SQLite 사용)
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 사용자 모델 정의 (데이터베이스 테이블 구조)
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)  # 비밀번호는 해시 형태로 저장

# 데이터베이스 초기화 (테이블 생성)
Base.metadata.create_all(bind=engine)

# 의존성: 데이터베이스 세션 생성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 비밀번호 검증 함수
def verify_password(plain_password, hashed_password):
    """사용자가 입력한 비밀번호(평문)와 해시화된 비밀번호를 비교"""
    return pwd_context.verify(plain_password, hashed_password)

# 비밀번호 해시화 함수
def hash_password(password):
    """사용자가 입력한 비밀번호를 해시화하여 저장할 때 사용"""
    return pwd_context.hash(password)

# 로그인 요청 모델
class LoginRequest(BaseModel):
    username: str
    employee_no: int


# FastAPI 로그인 엔드포인트 확인
@app.post("/")
async def login(request: LoginRequest):
    conn = await get_db_connection()
    try:
        async with conn.cursor() as cursor:
            # 로그인 시도 로그
            print(f"로그인 시도 - username: {request.username}, employee_no: {request.employee_no}")
            await cursor.execute(
                "SELECT name, employee_no, position FROM employees WHERE name = %s AND employee_no = %s",
                (request.username, request.employee_no)
            )
            result = await cursor.fetchone()
            if not result:
                raise HTTPException(status_code=400, detail="Invalid username or employee number")

            name, employee_no, position = result
            print(f"로그인 성공 - Role: {position}")

            # pytz를 사용해 현재 시간을 한국 시간대로 설정
            kst = pytz.timezone('Asia/Seoul')
            current_time = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
            print(f"Current Time (KST): {current_time}")  # 로그로 현재 시간 확인

            await cursor.execute(
                "UPDATE employees SET last_login = %s WHERE employee_no = %s",
                (current_time, employee_no)
            )
            await conn.commit()

            return {"message": "Login successful", "role": position}
    finally:
        conn.close()


######################################### 로그아웃 ###########################################
@app.post("/")
async def logout():
    """
    로그아웃 엔드포인트:
    - 클라이언트의 세션을 종료하거나 쿠키를 삭제합니다.
    """
    # 로그아웃 관련 세션 삭제 및 응답 설정
    response = {"message": "로그아웃되었습니다."}
    # 여기서 필요한 경우 세션 정보를 삭제하는 로직 추가 가능
    return response

