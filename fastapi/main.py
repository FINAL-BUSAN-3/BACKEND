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
import aiohttp
from io import BytesIO
from datetime import datetime
import logging

app = FastAPI()
current_index = 0

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

@app.get("/model-deployment/model-select")
async def get_model_info():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT model_info_id, model_name, model_version, python_version, library, model_type, loss, accuracy "
                "FROM model_info"
            )
            result = await cursor.fetchall()
            conn.close()

            # 데이터 가공: 모델 정보 목록 생성
            models = [
                {
                    "model_info_id": row[0],
                    "model_name": row[1],
                    "model_version": row[2],
                    "python_version": row[3],
                    "library": row[4],
                    "model_type": row[5],
                    "loss": row[6],
                    "accuracy": row[7],
                } for row in result
            ] if result else []

            return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/model-deployment/deploy-previous-model")
async def deploy_previous_model(model_info_id: str, deployment_date: str):
    conn = await get_db_connection()
    async with conn.cursor() as cursor:
        try:
            # model_info 테이블에서 deployment_date 업데이트
            await cursor.execute(
                "UPDATE model_info SET deployment_date = %s WHERE model_info_id = %s",
                (deployment_date, model_info_id)
            )

            # model_use 테이블에서 모든 상태를 0으로 업데이트
            await cursor.execute("UPDATE model_use SET model_use_state = 0")

            # 선택된 모델의 상태를 1로 업데이트
            await cursor.execute(
                "UPDATE model_use SET model_use_state = 1 WHERE model_use_id = %s",
                (model_info_id,)
            )

            await conn.commit()
            return {"message": "배포가 성공적으로 완료되었습니다."}
        except Exception as e:
            await conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()

# models 테이블의 데이터를 가져오는 엔드포인트 추가
@app.get("/model-deployment/model-info/{model_id}")
async def get_model_info(model_id: str):
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT model_name, model_version, python_version, library, model_type, loss, accuracy "
                "FROM model_info WHERE model_info_id = %s", (model_id,)
            )
            result = await cursor.fetchone()
            conn.close()
            if result:
                return {
                    "model_name": result[0],
                    "model_version": result[1],
                    "python_version": result[2],
                    "library": result[3],
                    "model_type": result[4],
                    "loss": result[5],
                    "accuracy": result[6],
                }
            else:
                raise HTTPException(status_code=404, detail="Model not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# /model-deployment/model-detail 엔드포인트
@app.get("/model-deployment/model-detail")
async def get_active_model_info():
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            # state가 1인 모델 ID를 model_use 테이블에서 가져옴
            await cursor.execute("SELECT model_use_id FROM model_use WHERE model_use_state = 1 LIMIT 1")
            result = await cursor.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="No active model found")

            model_info_id = result[0]

            # model_info 테이블에서 해당 모델의 상세 정보 가져오기
            await cursor.execute("""
                SELECT model_name, model_version, python_version, library, model_type, loss, accuracy
                FROM model_info WHERE model_info_id = %s
            """, (model_info_id,))
            model_info = await cursor.fetchone()

            if not model_info:
                raise HTTPException(status_code=404, detail="Model information not found")

            # 결과를 딕셔너리 형태로 반환
            return {
                "model_name": model_info[0],
                "model_version": model_info[1],
                "python_version": model_info[2],
                "library": model_info[3],
                "model_type": model_info[4],
                "loss": model_info[5],
                "accuracy": model_info[6],
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


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
                    "press_time_ms": row[4],
                    "pressure_1": row[5],
                    "pressure_2": row[6],
                    "pressure_5": row[7],
                }
                for row in result
            ] if result else []

            return {"press_raw_data": press_raw_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/engineering/realtime-welding/insert")
async def get_realtime_welding_insert():
    global current_index
    try:
        conn = await get_db_welding_connection()  # DB 연결
        async with conn.cursor() as cursor:
            # 현재 인덱스 기준으로 데이터 하나 가져오기
            query = f"SELECT * FROM welding_raw_data LIMIT 1 OFFSET {current_index}"
            await cursor.execute(query)
            result = await cursor.fetchall()

            # 다음 호출을 위해 인덱스 업데이트
            if result:
                current_index += 1
                welding_raw_data = [
                    {
                        "idx": row[0],
                        "machine_name": row[1],
                        "item_no": row[2],
                        "working_time": row[3],
                        "thickness_1_mm": row[4],
                        "thickness_2_mm": row[5],
                        "welding_force_bar": row[6],
                        "welding_current_ka": row[7],
                        "weld_voltage_v": row[8],
                        "weld_time_ms": row[9]
                    }
                    for row in result
                ]
                return {"welding_raw_data": welding_raw_data}
            else:
                # 데이터가 없을 경우 인덱스 초기화 (순환 시작)
                current_index = 0
                return {"message": "No more data available, resetting index."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Colab ngrok API 주소 설정
NGROK_MODEL_API = "https://9852-34-145-79-187.ngrok-free.app/engineering/realtime-welding/predict"
# 로그 설정
logging.basicConfig(level=logging.INFO)

@app.get("/engineering/realtime-welding/select")
async def select_and_predict_welding_quality():
    try:
        # 데이터 가져오기 확인
        logging.info("Fetching welding data from insert endpoint")
        welding_data = await get_realtime_welding_insert()
        raw_data = welding_data["welding_raw_data"][0]  # 첫 번째 데이터 추출

        # ngrok API에 필요한 컬럼만 선택하여 데이터 형식 맞추기
        sample_data = [
            float(raw_data["welding_force_bar"]),
            float(raw_data["welding_current_ka"]),
            float(raw_data["weld_voltage_v"]),
            float(raw_data["weld_time_ms"])
        ]

        # 전송할 데이터 형식 맞추기
        payload = {"data": sample_data}
        logging.info(f"Sending formatted data to ngrok API: {payload}")

        # ngrok API에 POST 요청 전송
        async with aiohttp.ClientSession() as session:
            async with session.post(NGROK_MODEL_API, json=payload) as response:
                if response.status == 200:
                    prediction_result = await response.json()
                    logging.info(f"Received prediction result: {prediction_result}")
                    return {
                        "prediction": prediction_result.get("prediction")
                    }
                else:
                    error_message = f"Failed to get prediction from ngrok API, Status: {response.status}"
                    logging.error(error_message)
                    raise HTTPException(status_code=response.status, detail=error_message)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))