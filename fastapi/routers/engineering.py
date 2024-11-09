from fastapi import FastAPI, WebSocket, WebSocketDisconnect, APIRouter, HTTPException
from database import get_db_press_connection, get_db_welding_connection
import aiohttp
import asyncio
import logging
from datetime import datetime
import json

app = FastAPI()
router = APIRouter()

# 실시간 INDEX 변수 및 잠금 설정
current_index_welding = None
current_index_press = None
shared_trend_time_welding = None
shared_trend_time_press = None
welding_lock = asyncio.Lock()  # Welding 인덱스에 대한 잠금
press_lock = asyncio.Lock()     # Press 인덱스에 대한 잠금
# 외부 API URL 설정
NGROK_WELDING_MODEL_API = "https://9fc7-34-168-25-223.ngrok-free.app/engineering/realtime-welding/predict"
NGROK_PRESS_MODEL_API = "https://9fc7-34-168-25-223.ngrok-free.app/engineering/realtime-press/predict"

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# 홈 엔드포인트
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
    return {"message": "프레스 트렌드 데이터"}

@router.get("/realtime-welding/trend")
async def realtime_welding_trend():
    return {"message": "웰딩 트렌드 데이터"}


# Utility function to serialize datetime to string
def datetime_to_str(dt):
    return dt if isinstance(dt, str) else dt.isoformat() if dt else None

@router.websocket("/ws/realtime-welding/insert")
async def websocket_realtime_welding_insert(websocket: WebSocket):
    await websocket.accept()
    global shared_trend_time_welding, current_index_welding

    if current_index_welding is None:
        current_index_welding = 0

    try:
        while True:
            welding_start_time = datetime.now()
            async with welding_lock:
                conn = await get_db_welding_connection()
                async with conn.cursor() as cursor:
                    query = f"SELECT * FROM welding_raw_data LIMIT 1 OFFSET {current_index_welding}"
                    await cursor.execute(query)
                    result = await cursor.fetchall()
                    if result:
                        # trend_time을 설정하여 select에서도 동일하게 참조
                        shared_trend_time_welding = datetime.now()
                        welding_data = {
                            "machine_name": result[0][1],
                            "item_no": result[0][2],
                            "working_time": datetime_to_str(result[0][3]),
                            "trend_time": datetime_to_str(shared_trend_time_welding),
                            "thickness_1_mm": result[0][4],
                            "thickness_2_mm": result[0][5],
                            "welding_force_bar": result[0][6],
                            "welding_current_ka": result[0][7],
                            "weld_voltage_v": result[0][8],
                            "weld_time_ms": result[0][9]
                        }

                        insert_query = """
                            INSERT INTO WELDING_INSERT_TREND (machine_name, item_no, working_time, thickness_1_mm, thickness_2_mm,
                                                              welding_force_bar, welding_current_ka, weld_voltage_v, weld_time_ms, trend_time)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        await cursor.execute(insert_query, (
                            welding_data["machine_name"], welding_data["item_no"], welding_data["working_time"],
                            welding_data["thickness_1_mm"], welding_data["thickness_2_mm"],
                            welding_data["welding_force_bar"], welding_data["welding_current_ka"],
                            welding_data["weld_voltage_v"], welding_data["weld_time_ms"], shared_trend_time_welding,
                        ))
                        await conn.commit()

                        await websocket.send_json(welding_data)
                        current_index_welding += 1
                    else:
                        current_index_welding = 0
                        await websocket.send_json({"message": "더 이상 데이터가 없어 인덱스를 초기화합니다."})

            elapsed_time = (datetime.now() - welding_start_time).total_seconds()
            await asyncio.sleep(max(0, 5 - elapsed_time))
    except WebSocketDisconnect:
        logging.info("Client disconnected from welding insert websocket")
        await websocket.close()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await websocket.close()

@router.websocket("/ws/realtime-welding/select")
async def websocket_realtime_welding_select(websocket: WebSocket):
    await websocket.accept()
    global shared_trend_time_welding, current_index_welding

    if current_index_welding is None:
        current_index_welding = 0

    try:
        while True:
            welding_start_time = datetime.now()
            async with welding_lock:
                conn = await get_db_welding_connection()
                async with conn.cursor() as cursor:
                    select_index = max(0, current_index_welding - 1)
                    query = f"SELECT * FROM welding_raw_data LIMIT 1 OFFSET {select_index}"
                    await cursor.execute(query)
                    result = await cursor.fetchall()

                    if not result:
                        await websocket.send_json({"message": "예측을 위한 데이터가 없습니다."})
                        current_index_welding = 0
                        continue

                    raw_welding_data = {
                        "welding_force_bar": result[0][6],
                        "welding_current_ka": result[0][7],
                        "weld_voltage_v": result[0][8],
                        "weld_time_ms": result[0][9]
                    }

                    sample_welding_data = [
                        float(raw_welding_data["welding_force_bar"]),
                        float(raw_welding_data["welding_current_ka"]),
                        float(raw_welding_data["weld_voltage_v"]),
                        float(raw_welding_data["weld_time_ms"])
                    ]

                    welding_payload = {"data": sample_welding_data}
                    async with aiohttp.ClientSession() as session:
                        async with session.post(NGROK_WELDING_MODEL_API, json=welding_payload) as response:
                            if response.status == 200:
                                welding_prediction_result = await response.json()
                                prediction = welding_prediction_result.get("prediction")

                                insert_query = """
                                    INSERT INTO WELDING_SELECT_TREND (trend_time, prediction)
                                    VALUES (%s, %s)
                                """
                                await cursor.execute(insert_query, (shared_trend_time_welding, prediction))
                                await conn.commit()

                                await websocket.send_json({"welding_prediction": prediction})
                            else:
                                await websocket.send_json({"message": f"예측 API가 상태 {response.status}로 실패했습니다."})

            elapsed_time = (datetime.now() - welding_start_time).total_seconds()
            await asyncio.sleep(max(0, 5 - elapsed_time))
    except WebSocketDisconnect:
        logging.info("Client disconnected from welding select websocket")
        await websocket.close()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await websocket.close()

@router.websocket("/ws/realtime-press/insert")
async def websocket_realtime_press_insert(websocket: WebSocket):
    await websocket.accept()
    global shared_trend_time_press, current_index_press

    if current_index_press is None:
        current_index_press = 0

    try:
        while True:
            press_start_time = datetime.now()
            async with press_lock:
                conn = await get_db_press_connection()
                async with conn.cursor() as cursor:
                    query = f"SELECT * FROM press_raw_data LIMIT 1 OFFSET {current_index_press}"
                    await cursor.execute(query)
                    result = await cursor.fetchall()
                    if result:
                        shared_trend_time_press = datetime.now()
                        press_data = {
                            "machine_name": result[0][1],
                            "item_no": result[0][2],
                            "working_time": datetime_to_str(result[0][3]),
                            "trend_time": datetime_to_str(shared_trend_time_press),
                            "press_time_ms": result[0][4],
                            "pressure_1": result[0][5],
                            "pressure_2": result[0][6],
                            "pressure_5": result[0][7],
                        }

                        insert_query = """
                            INSERT INTO PRESS_INSERT_TREND (machine_name, item_no, working_time, press_time_ms, pressure_1, pressure_2, pressure_5, trend_time)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        await cursor.execute(insert_query, (
                            press_data["machine_name"], press_data["item_no"], press_data["working_time"],
                            press_data["press_time_ms"], press_data["pressure_1"],
                            press_data["pressure_2"], press_data["pressure_5"], shared_trend_time_press
                        ))
                        await conn.commit()

                        await websocket.send_json(press_data)
                        current_index_press += 1
                    else:
                        current_index_press = 0
                        await websocket.send_json({"message": "더 이상 데이터가 없어 인덱스를 초기화합니다."})

            elapsed_time = (datetime.now() - press_start_time).total_seconds()
            await asyncio.sleep(max(0, 5 - elapsed_time))
    except WebSocketDisconnect:
        logging.info("Client disconnected from press insert websocket")
        await websocket.close()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await websocket.close()

@router.websocket("/ws/realtime-press/select")
async def websocket_realtime_press_select(websocket: WebSocket):
    await websocket.accept()
    global shared_trend_time_press, current_index_press

    if current_index_press is None:
        current_index_press = 0

    try:
        while True:
            press_start_time = datetime.now()
            async with press_lock:
                conn = await get_db_press_connection()
                async with conn.cursor() as cursor:
                    select_index = max(0, current_index_press - 1)
                    query = f"SELECT * FROM press_raw_data LIMIT 1 OFFSET {select_index}"
                    await cursor.execute(query)
                    result = await cursor.fetchall()

                    if not result:
                        await websocket.send_json({"message": "예측을 위한 데이터가 없습니다."})
                        current_index_press = 0
                        continue

                    raw_press_data = {
                        "pressure_1": result[0][5],
                        "pressure_2": result[0][6]
                    }

                    sample_press_data = [
                        float(raw_press_data["pressure_1"]),
                        float(raw_press_data["pressure_2"])
                    ]

                    press_payload = {"data": sample_press_data}
                    async with aiohttp.ClientSession() as session:
                        async with session.post(NGROK_PRESS_MODEL_API, json=press_payload) as response:
                            if response.status == 200:
                                press_prediction_result = await response.json()
                                prediction = press_prediction_result.get("prediction")

                                insert_query = """
                                    INSERT INTO PRESS_SELECT_TREND (trend_time, prediction)
                                    VALUES (%s, %s)
                                """
                                await cursor.execute(insert_query, (shared_trend_time_press, prediction))
                                await conn.commit()

                                await websocket.send_json({"press_prediction": prediction})
                            else:
                                await websocket.send_json({"message": f"예측 API가 상태 {response.status}로 실패했습니다."})

            elapsed_time = (datetime.now() - press_start_time).total_seconds()
            await asyncio.sleep(max(0, 5 - elapsed_time))
    except WebSocketDisconnect:
        logging.info("Client disconnected from press select websocket")
        await websocket.close()
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await websocket.close()