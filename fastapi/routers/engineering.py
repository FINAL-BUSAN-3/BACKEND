from fastapi import APIRouter, HTTPException
from database import get_db_press_connection, get_db_welding_connection
import aiohttp
import logging

router = APIRouter()
current_index = 0

# 외부 API URL 설정
NGROK_MODEL_API = "https://4c6d-34-45-140-254.ngrok-free.app/engineering/realtime-welding/predict"

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# -------------------------------
# 홈 엔드포인트
# -------------------------------

@router.get("/")
async def management_home():
    return {"message": "엔지니어링 홈에 오신 것을 환영합니다"}

@router.get("/press")
async def engineering_press_home():
    return {"message": "엔지니어링 프레스 홈"}

@router.get("/welding")
async def engineering_welding_home():
    return {"message": "엔지니어링 웰딩 홈"}

# -------------------------------
# 실시간 프레스 데이터 엔드포인트
# -------------------------------

@router.get("/realtime-press/insert")
async def get_realtime_press_insert():
    """실시간 프레스 데이터 한 항목 가져오기"""
    try:
        conn = await get_db_press_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM press_raw_data LIMIT 1")
            result = await cursor.fetchall()
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
                } for row in result
            ] if result else []
            return {"press_raw_data": press_raw_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime-press/select")
async def realtime_press_select():
    """특정 실시간 프레스 데이터 선택"""
    return {"message": "실시간 프레스 데이터 선택"}

@router.get("/realtime-press/trend")
async def realtime_press_trend():
    """프레스 트렌드 데이터 가져오기"""
    return {"message": "프레스 트렌드 데이터"}

# -------------------------------
# 실시간 웰딩 데이터 엔드포인트
# -------------------------------

@router.get("/realtime-welding/insert")
async def get_realtime_welding_insert():
    """실시간 웰딩 데이터 한 항목 가져오기 및 인덱스 자동 증가"""
    global current_index
    try:
        conn = await get_db_welding_connection()
        async with conn.cursor() as cursor:
            query = f"SELECT * FROM welding_raw_data LIMIT 1 OFFSET {current_index}"
            await cursor.execute(query)
            result = await cursor.fetchall()
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
                    } for row in result
                ]
                return {"welding_raw_data": welding_raw_data}
            else:
                current_index = 0
                return {"message": "더 이상 데이터가 없으므로 인덱스를 초기화합니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime-welding/select")
async def select_and_predict_welding_quality():
    """실시간 웰딩 데이터 가져오기 및 품질 예측"""
    try:
        logging.info("Insert 엔드포인트에서 웰딩 데이터 가져오는 중")
        welding_data = await get_realtime_welding_insert()
        raw_data = welding_data["welding_raw_data"][0]  # 첫 번째 데이터 가져오기

        sample_data = [
            float(raw_data["welding_force_bar"]),
            float(raw_data["welding_current_ka"]),
            float(raw_data["weld_voltage_v"]),
            float(raw_data["weld_time_ms"])
        ]

        payload = {"data": sample_data}
        logging.info(f"데이터를 ngrok API로 전송: {payload}")

        async with aiohttp.ClientSession() as session:
            async with session.post(NGROK_MODEL_API, json=payload) as response:
                if response.status == 200:
                    prediction_result = await response.json()
                    logging.info(f"예측 결과 받음: {prediction_result}")
                    return {"prediction": prediction_result.get("prediction")}
                else:
                    error_message = f"ngrok API 예측 실패, 상태: {response.status}"
                    logging.error(error_message)
                    raise HTTPException(status_code=response.status, detail=error_message)
    except Exception as e:
        logging.error(f"오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime-welding/trend")
async def realtime_welding_trend():
    """웰딩 트렌드 데이터 가져오기"""
    return {"message": "웰딩 트렌드 데이터"}
