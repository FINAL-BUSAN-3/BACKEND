from fastapi import APIRouter, HTTPException
from database import get_db_press_connection, get_db_welding_connection
import aiohttp
import asyncio
import logging
from datetime import datetime  # datetime 모듈 임포트

router = APIRouter()

# 실시간 INDEX 변수 및 잠금 설정
current_index_welding = 0
current_index_press = 0
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

@router.get("/realtime-welding/insert")
async def get_realtime_welding_insert():
    """실시간 웰딩 데이터 한 항목 가져오기 및 인덱스 자동 증가"""
    global current_index_welding
    async with welding_lock:
        try:
            conn = await get_db_welding_connection()
            async with conn.cursor() as cursor:
                query = f"SELECT * FROM welding_raw_data LIMIT 1 OFFSET {current_index_welding}"
                await cursor.execute(query)
                result = await cursor.fetchall()
                if result:
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
                    current_index_welding += 1
                    return {"welding_data": welding_data}
                else:
                    current_index_welding = 0
                    return {"message": "더 이상 데이터가 없으므로 인덱스를 초기화합니다."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/realtime-welding/select")
async def select_and_predict_welding_quality():
    """실시간 웰딩 데이터 가져오기 및 품질 예측"""
    global current_index_welding
    async with welding_lock:
        try:
            conn = await get_db_welding_connection()
            async with conn.cursor() as cursor:
                query = f"SELECT * FROM welding_raw_data LIMIT 1 OFFSET {current_index_welding - 1}"
                await cursor.execute(query)
                result = await cursor.fetchall()
                if not result:
                    raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")

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
                            return {"welding_prediction": welding_prediction_result.get("prediction")}
                        else:
                            raise HTTPException(status_code=response.status, detail="예측 실패")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime-press/insert")
async def get_realtime_press_insert():
    """Insert a new press data row into the press_trend table without updating the prediction column."""
    global current_index_press
    async with press_lock:
        try:
            conn = await get_db_press_connection()
            async with conn.cursor() as cursor:
                query = f"SELECT * FROM press_raw_data LIMIT 1 OFFSET {current_index_press}"
                await cursor.execute(query)
                result = await cursor.fetchall()
                if result:
                    press_data = [
                        {
                            "machine_name": row[1],
                            "item_no": row[2],
                            "working_time": row[3],
                            "press_time_ms": row[4],
                            "pressure_1": row[5],
                            "pressure_2": row[6],
                            "pressure_5": row[7],
                        } for row in result
                    ]
                    # Insert data row without prediction
                    insert_query = """
                        INSERT INTO press_trend (machine_name, item_no, working_time, press_time_ms, pressure_1, pressure_2, pressure_5, trend_time)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    trend_time = datetime.now()
                    for row in result:
                        await cursor.execute(insert_query, (
                            row[1], row[2], row[3], row[4], row[5], row[6], row[7], trend_time
                        ))
                    await conn.commit()

                    current_index_press += 1
                    return {"press_data": press_data}
                else:
                    current_index_press = 0
                    return {"message": "No more data; resetting index."}
        except Exception as e:
            logging.error(f"Error in get_realtime_press_insert: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/realtime-press/select")
async def select_and_predict_press_quality():
    """Predict and update the prediction column in the most recent row of press_trend without inserting new data rows."""
    async with press_lock:
        try:
            conn = await get_db_press_connection()
            async with conn.cursor() as cursor:
                # Prepare prediction data from the most recent inserted data
                query = "SELECT pressure_1, pressure_2 FROM press_trend ORDER BY idx DESC LIMIT 1"
                await cursor.execute(query)
                result = await cursor.fetchall()
                if not result:
                    raise HTTPException(status_code=404, detail="No data found for prediction.")

                # Use retrieved data for prediction
                sample_press_data = [
                    float(result[0][0]),  # pressure_1
                    float(result[0][1])  # pressure_2
                ]

                press_payload = {"data": sample_press_data}
                logging.info(f"Sending press data to ngrok API: {press_payload}")

                # Call prediction API and update the latest row
                async with aiohttp.ClientSession() as session:
                    async with session.post(NGROK_PRESS_MODEL_API, json=press_payload) as response:
                        if response.status == 200:
                            press_prediction_result = await response.json()
                            prediction = press_prediction_result.get("prediction")

                            # Update prediction in the most recent row
                            update_prediction_query = """
                                UPDATE press_trend
                                SET prediction = %s
                                ORDER BY idx DESC
                                LIMIT 1
                            """
                            await cursor.execute(update_prediction_query, (prediction,))
                            await conn.commit()

                            logging.info(f"Received press prediction result: {press_prediction_result}")
                            return {"press_prediction": prediction}
                        else:
                            error_message = f"Failed to get prediction from ngrok API, status: {response.status}"
                            logging.error(error_message)
                            raise HTTPException(status_code=response.status, detail=error_message)
        except Exception as e:
            logging.error(f"Error in select_and_predict_press_quality: {e}")
            raise HTTPException(status_code=500, detail=str(e))
