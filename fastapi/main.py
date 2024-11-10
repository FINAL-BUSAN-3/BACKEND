from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends #로그인

from controllers import test_controller
from superset import get_superset_data
import mysql.connector
from mysql.connector import Error
import pkgutil
import importlib
import aiomysql
from pydantic import BaseModel
from typing import Optional, List, Dict
import aiohttp
from io import BytesIO
from datetime import datetime
import logging
import pytz

#비밀번호 암호화를 위한 라이브러리
from passlib.context import CryptContext
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from database import get_db_connection
import asyncio
import uvicorn

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 전역 변수 선언
current_index_welding = 0
current_index_press = 0
shared_trend_time_welding = datetime.now()
shared_trend_time_press = datetime.now()
updater_running = False  # 중복 실행 방지 플래그

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 라우터 자동 등록
def register_routers(app):
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


# 정확히 5초마다 index를 증가시키는 비동기 태스크
async def index_updater():
    global current_index_welding, current_index_press, updater_running
    if updater_running:
        logger.info("Index updater is already running.")
        return  # 중복 실행 방지

    updater_running = True
    try:
        while True:
            start_time = datetime.now()
            current_index_welding += 1
            current_index_press += 1
            logger.info(f"Updated index: welding={current_index_welding}, press={current_index_press}")

            # 정확히 5초 주기로 실행
            elapsed_time = (datetime.now() - start_time).total_seconds()
            await asyncio.sleep(max(0, 5 - elapsed_time))
    except Exception as e:
        logger.error(f"Error in index updater: {e}")
    finally:
        updater_running = False


# FastAPI 앱 시작 시 index_updater 함수를 실행
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(index_updater())


# 라우터 등록
register_routers(app)


# 컨트롤러의 라우터를 애플리케이션에 포함
app.include_router(test_controller.router)
register_routers(app)

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id, "name": f"Item {item_id}"}

@app.get("/superset-data")
async def superset_data():
    try:
        data = await get_superset_data()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
async def test_endpoint():
    return {"message": "Hello from FastAPI!"}



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
# @app.post("/")
# async def logout():
#     """
#     로그아웃 엔드포인트:
#     - 클라이언트의 세션을 종료하거나 쿠키를 삭제합니다.
#     """
#     # 로그아웃 관련 세션 삭제 및 응답 설정
#     response = {"message": "로그아웃되었습니다."}
#     # 여기서 필요한 경우 세션 정보를 삭제하는 로직 추가 가능
#     return response
#
