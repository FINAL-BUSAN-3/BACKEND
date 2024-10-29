from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from controllers import test_controller
from superset import get_superset_data
import mysql.connector
from mysql.connector import Error
import pkgutil
import importlib
import aiomysql
from pydantic import BaseModel
from typing import Optional
from io import BytesIO
from datetime import datetime

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# MySQL web 연결 설정 함수
async def get_db_connection():
    return await aiomysql.connect(
        host='opyter.iptime.org',
        user='bigdata_busan_3',
        password='busan12345678*',
        db='web',
        port=3306
    )

# MySQL press 연결 설정 함수
async def get_db_press_connection():
    return await aiomysql.connect(
        host='opyter.iptime.org',
        user='bigdata_busan_3',
        password='busan12345678*',
        db='press',
        port=3306
    )

# MySQL welding 연결 설정 함수
async def get_db_welding_connection():
    return await aiomysql.connect(
        host='opyter.iptime.org',
        user='bigdata_busan_3',
        password='busan12345678*',
        db='welding',
        port=3306
    )


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


class User(BaseModel):
    name: str
    employeeNo: int
    role: str

class Group(BaseModel):
    groupName: str
    groupDescription: str

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

class UpdateUser(BaseModel):
    id: int
    position: str

@app.put("/user-management/user-detail/{user_id}")
async def update_user_detail(user_id: int, user: UpdateUser):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "UPDATE employees SET position = %s WHERE employee_no = %s",
                (user.position, user_id)
            )
            await conn.commit()
            conn.close()
            return {"message": "사용자 정보가 성공적으로 업데이트되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user-management/user-detail/{user_id}")
async def get_user_detail(user_id: int):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT name, employee_no, position, last_login FROM employees WHERE employee_no = %s", (user_id,)
            )
            result = await cursor.fetchone()
            conn.close()
            if result:
                user = {
                    "name": result[0],
                    "employeeNo": result[1],
                    "position": result[2],
                    "lastLogin": result[3]
                }
                return user
            else:
                raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# models 테이블의 데이터를 가져오는 엔드포인트 추가
@app.get("/model-deployment/model-select")
async def get_model_file_names():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT model_info_id FROM model_info")
            result = await cursor.fetchall()
            conn.close()

            # 데이터 가공: 모델 파일 이름 목록 생성
            model_file_names = [row[0] for row in result] if result else []

            return {"model_file_names": model_file_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 모델 데이터 정의
class ModelData(BaseModel):
    model_name: str
    model_version: str
    python_version: str
    library: str
    model_type: str
    loss: float
    accuracy: float
    deployment_date: str


@app.post("/model-deployment/model-apply")
async def model_apply(
        model_name: str = Form(...),
        model_version: str = Form(...),
        python_version: str = Form(...),
        library: str = Form(...),
        deployment_date: str = Form(...),  # 형식: "YYYY-MM-DD HH:MM:SS"
        model_type : str = Form(...),
        loss: float = Form(...),
        accuracy: float = Form(...),
        file: Optional[UploadFile] = File(None)
):
    conn = await get_db_connection()
    async with conn.cursor() as cursor:
        try:
            # 파일 처리
            file_content = None
            if file:
                file_content = await file.read()
                print("파일 이름:", file.filename)
                print("파일 크기:", len(file_content))

            # deployment_date를 원하는 형식으로 변환
            date_part = deployment_date[2:10]  # 날짜 부분 YYYY-MM-DD
            time_part = deployment_date[11:16].replace(":", "-")  # 시간 부분 HH-MM
            model_info_id = f"{model_name}-{date_part}-{time_part}"
            print("저장할 모델 ID:", model_info_id)

            # model_info 테이블에 데이터 삽입
            insert_model_info = """
                INSERT INTO model_info 
                (model_info_id, model_name, model_version, python_version, library, model_type, deployment_date, loss, accuracy, model_info_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            await cursor.execute(insert_model_info, (
                model_info_id, model_name, model_version, python_version, library, model_type, deployment_date, loss, accuracy, file_content
            ))

            # model_use 테이블의 기존 레코드 상태 업데이트
            await cursor.execute("UPDATE model_use SET model_use_state = 0")

            # model_use 테이블에 새로운 레코드 추가
            insert_model_use = """
                INSERT INTO model_use 
                (model_use_id, model_use_state, model_use_file) 
                VALUES (%s, %s, %s)
            """
            await cursor.execute(insert_model_use, (model_info_id, 1, file_content))

            # 변경 사항 커밋
            await conn.commit()

            return {
                "message": "데이터가 MySQL에 성공적으로 저장되었습니다.",
                "model_info_id": model_info_id,
                "file_uploaded": bool(file)
            }
        except Exception as e:
            await conn.rollback()
            print("오류 발생:", str(e))
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()

@app.get("/engineering/realtime-press/insert")
async def get_realtime_press_insert():
    try:
        conn = await get_db_press_connection()  # 올바른 함수 이름 확인
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM press_raw_data limit 1")
            result = await cursor.fetchall()

            # 데이터 가공: 모든 열의 데이터를 포함한 객체 배열로 변환
            press_raw_data = [
                {
                    "idx": row[0],
                    "machine_name": row[1],
                    "item_no": row[2],
                    "working_time": row[3],
                    "press_time(ms)": row[4],
                    "pressure_1": row[5],
                    "pressure_2": row[6],
                    "pressure_5": row[7],
                }
                for row in result
            ] if result else []

            return {"press_raw_data": press_raw_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))