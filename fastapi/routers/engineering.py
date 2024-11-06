from fastapi import APIRouter, HTTPException
from database import get_db_press_connection, get_db_welding_connection
import aiohttp
import logging

router = APIRouter()

# 실시간 INDEX 변수 설정
current_index_welding = 0
current_index_press = 0

# 외부 API URL 설정
NGROK_WELDING_MODEL_API = "https://2856-34-169-34-10.ngrok-free.app/engineering/realtime-welding/predict"
NGROK_PRESS_MODEL_API = "https://2856-34-169-34-10.ngrok-free.app/engineering/realtime-press/predict"

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

@router.get("/realtime-press/trend")
async def realtime_press_trend():
    """프레스 트렌드 데이터 가져오기"""
    return {"message": "프레스 트렌드 데이터"}

@router.get("/realtime-welding/trend")
async def realtime_welding_trend():
    """웰딩 트렌드 데이터 가져오기"""
    return {"message": "웰딩 트렌드 데이터"}

#=======================================================================
#                          실시간 웰딩 엔드 포인트
#=======================================================================
@router.get("/realtime-welding/insert")
async def get_realtime_welding_insert():
    """실시간 웰딩 데이터 한 항목 가져오기 및 인덱스 자동 증가"""
    global current_index_welding
    try:
        conn = await get_db_welding_connection()
        async with conn.cursor() as cursor:
            query = f"SELECT * FROM welding_raw_data LIMIT 1 OFFSET {current_index_welding}"
            await cursor.execute(query)
            result = await cursor.fetchall()
            if result:
                current_index_welding += 1
                welding_data = [
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
                return {"welding_data": welding_data}
            else:
                current_index_welding = 0
                return {"message": "더 이상 데이터가 없으므로 인덱스를 초기화합니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime-welding/select")
async def select_and_predict_welding_quality():
    """실시간 웰딩 데이터 가져오기 및 품질 예측"""
    try:
        logging.info("Insert 엔드포인트에서 웰딩 데이터 가져오는 중")
        welding_data = await get_realtime_welding_insert()
        raw_welding_data = welding_data["welding_data"][0]  # 첫 번째 데이터 가져오기

        sample_welding_data = [
            float(raw_welding_data["welding_force_bar"]),
            float(raw_welding_data["welding_current_ka"]),
            float(raw_welding_data["weld_voltage_v"]),
            float(raw_welding_data["weld_time_ms"])
        ]

        welding_payload = {"data": sample_welding_data}
        logging.info(f"웰딩 데이터를 ngrok API로 전송: {welding_payload}")

        async with aiohttp.ClientSession() as session:
            async with session.post(NGROK_WELDING_MODEL_API, json=welding_payload) as response:
                if response.status == 200:
                    welding_prediction_result = await response.json()
                    logging.info(f"웰딩 예측 결과 받음: {welding_prediction_result}")
                    return {"welding_prediction": welding_prediction_result.get("prediction")}
                else:
                    error_message = f"ngrok API 웰딩 예측 실패, 상태: {response.status}"
                    logging.error(error_message)
                    raise HTTPException(status_code=response.status, detail=error_message)
    except Exception as e:
        logging.error(f"오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime-welding/trend")
async def realtime_welding_trend():
    """웰딩 트렌드 데이터 가져오기"""
    return {"message": "웰딩 트렌드 데이터"}

#=======================================================================
#                          실시간 프레스 엔드 포인트
#=======================================================================

@router.get("/realtime-press/insert")
async def get_realtime_press_insert():
    """실시간 프레스 데이터 한 항목 가져오기 및 인덱스 자동 증가"""
    global current_index_press
    try:
        conn = await get_db_press_connection()
        async with conn.cursor() as cursor:
            query = f"SELECT * FROM press_raw_data LIMIT 1 OFFSET {current_index_press}"
            await cursor.execute(query)
            result = await cursor.fetchall()
            if result:
                current_index_press += 1
                press_data = [
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
                ]
                return {"press_data": press_data}
            else:
                current_index_press = 0
                return {"message": "더 이상 데이터가 없으므로 인덱스를 초기화합니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime-press/select")
async def select_and_predict_press_quality():
    """실시간 프레스 데이터 가져오기 및 품질 예측"""
    try:
        logging.info("Insert 엔드포인트에서 프레스 데이터 가져오는 중")
        press_data = await get_realtime_press_insert()
        raw_press_data = press_data["press_data"][0]  # 첫 번째 데이터 가져오기

        sample_press_data = [
            float(raw_press_data["pressure_1"]),
            float(raw_press_data["pressure_2"])
        ]

        press_payload = {"data": sample_press_data}
        logging.info(f"프레스 데이터를 ngrok API로 전송: {press_payload}")

        async with aiohttp.ClientSession() as session:
            async with session.post(NGROK_PRESS_MODEL_API, json=press_payload) as response:
                if response.status == 200:
                    press_prediction_result = await response.json()
                    logging.info(f"프레스 예측 결과 받음: {press_prediction_result}")
                    return {"press_prediction": press_prediction_result.get("prediction")}
                else:
                    error_message = f"ngrok API 프레스 예측 실패, 상태: {response.status}"
                    logging.error(error_message)
                    raise HTTPException(status_code=response.status, detail=error_message)
    except Exception as e:
        logging.error(f"오류 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))
