from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from database import get_db_press_connection, get_db_welding_connection
import main
import aiohttp
import asyncio
import logging
import time
from datetime import datetime

# 라우터 생성
router = APIRouter()
logger = logging.getLogger(__name__)

# 잠금 객체
welding_lock = asyncio.Lock()
press_lock = asyncio.Lock()

# 외부 API URL 설정
NGROK_WELDING_MODEL_API = "https://6e61-34-145-12-93.ngrok-free.app/engineering/realtime-welding/predict"
NGROK_PRESS_MODEL_API = "https://6e61-34-145-12-93.ngrok-free.app/engineering/realtime-press/predict"

# welding_data와 press_data를 공유 변수로 설정
welding_data = None
press_data = None


# datetime을 문자열로 변환하는 유틸리티 함수
def datetime_to_str(dt):
    return dt if isinstance(dt, str) else dt.isoformat() if dt else None

# Welding Insert WebSocket
@router.websocket("/ws/realtime-welding/insert")
async def websocket_realtime_welding_insert(websocket: WebSocket):
    await websocket.accept()
    last_index_welding = None
    interval = 5  # 5초 주기

    try:
        while True:
            start_time = datetime.now().timestamp()

            # 예측이 중단된 상태가 아니면 데이터 처리
            if not main.all_operations_paused and main.current_index_welding != last_index_welding:
                last_index_welding = main.current_index_welding

                async with welding_lock:
                    conn = await get_db_welding_connection()
                    async with conn.cursor() as cursor:
                        query = f"SELECT * FROM welding_raw_data LIMIT 1 OFFSET {main.current_index_welding}"
                        await cursor.execute(query)
                        result = await cursor.fetchall()
                        if result:
                            main.shared_trend_time_welding = datetime.now()
                            global welding_data
                            welding_data = {
                                "machine_name": result[0][1],
                                "item_no": result[0][2],
                                "working_time": datetime_to_str(result[0][3]),
                                "trend_time": datetime_to_str(main.shared_trend_time_welding),
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
                                welding_data["weld_voltage_v"], welding_data["weld_time_ms"], main.shared_trend_time_welding,
                            ))
                            await conn.commit()

                            logger.info(f"웰딩 데이터 삽입 - trend_time: {main.shared_trend_time_welding}, 데이터: {welding_data}")
                            await websocket.send_json({"inserted_data": welding_data})
                        else:
                            main.current_index_welding = 0
                            await websocket.send_json({"message": "더 이상 데이터가 없어 인덱스를 초기화합니다."})

            elapsed_time = datetime.now().timestamp() - start_time
            await asyncio.sleep(max(0, interval - elapsed_time))

    except WebSocketDisconnect:
        logger.info("클라이언트가 웰딩 insert 웹소켓 연결을 끊었습니다.")
        await websocket.close()
    except Exception as e:
        logger.error(f"예기치 못한 오류: {e}")
        await websocket.close()

# Welding Select WebSocket
@router.websocket("/ws/realtime-welding/select")
async def websocket_realtime_welding_select(websocket: WebSocket):
    await websocket.accept()
    last_data_welding = None

    try:
        while True:
            await asyncio.sleep(0.1)

            if welding_data != last_data_welding:
                last_data_welding = welding_data

                async with welding_lock:
                    if welding_data is None or main.shared_trend_time_welding is None:
                        await websocket.send_json({"message": "현재 trend_time이 없습니다. Insert가 실행 중인지 확인하십시오."})
                        continue

                    sample_welding_data = [
                        float(welding_data["welding_force_bar"]),
                        float(welding_data["welding_current_ka"]),
                        float(welding_data["weld_voltage_v"]),
                        float(welding_data["weld_time_ms"])
                    ]
                    welding_payload = {"data": sample_welding_data}
                    async with aiohttp.ClientSession() as session:
                        async with session.post(NGROK_WELDING_MODEL_API, json=welding_payload) as response:
                            if response.status == 200:
                                welding_prediction_result = await response.json()
                                prediction = welding_prediction_result.get("prediction")

                                conn = await get_db_welding_connection()
                                async with conn.cursor() as cursor:
                                    insert_query = """
                                        INSERT INTO WELDING_SELECT_TREND (trend_time, prediction)
                                        VALUES (%s, %s)
                                    """
                                    await cursor.execute(insert_query, (main.shared_trend_time_welding, prediction))
                                    await conn.commit()

                                logger.info(f"예측 값 - trend_time: {main.shared_trend_time_welding}, 예측: {prediction}")
                                await websocket.send_json({"welding_prediction": prediction})

                                # 예측 값이 1일 때만 insert 멈추기
                                if prediction == 1:
                                    main.pause_all_operations()  # Insert만 멈춤
                                    await websocket.send_json({"stop_event": True})
                                else:
                                    # 예측 값이 0일 경우에도 인덱스를 증가시켜 다음 데이터로 이동
                                    main.current_index_welding += 1

                            else:
                                await websocket.send_json({"message": f"예측 API가 상태 {response.status}로 실패했습니다."})

    except WebSocketDisconnect:
        logger.info("클라이언트가 웰딩 select 웹소켓 연결을 끊었습니다.")
        await websocket.close()
    except Exception as e:
        logger.error(f"예기치 못한 오류: {e}")
        await websocket.close()


# Press Insert WebSocket
@router.websocket("/ws/realtime-press/insert")
async def websocket_realtime_press_insert(websocket: WebSocket):
    await websocket.accept()
    last_index_press = None
    interval = 5  # 5초 주기

    try:
        while True:
            start_time = datetime.now().timestamp()

            # 예측이 중단된 상태가 아니면 데이터 처리
            if not main.all_operations_paused and main.current_index_press != last_index_press:
                last_index_press = main.current_index_press

                async with press_lock:
                    conn = await get_db_press_connection()
                    async with conn.cursor() as cursor:
                        query = f"SELECT * FROM press_raw_data LIMIT 1 OFFSET {main.current_index_press}"
                        await cursor.execute(query)
                        result = await cursor.fetchall()
                        if result:
                            main.shared_trend_time_press = datetime.now()
                            global press_data
                            press_data = {
                                "machine_name": result[0][1],
                                "item_no": result[0][2],
                                "working_time": datetime_to_str(result[0][3]),
                                "trend_time": datetime_to_str(main.shared_trend_time_press),
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
                                press_data["pressure_2"], press_data["pressure_5"], main.shared_trend_time_press
                            ))
                            await conn.commit()

                            logger.info(f"프레스 데이터 삽입 - trend_time: {main.shared_trend_time_press}, 데이터: {press_data}")
                            await websocket.send_json({"inserted_data": press_data})
                        else:
                            main.current_index_press = 0
                            await websocket.send_json({"message": "더 이상 데이터가 없어 인덱스를 초기화합니다."})

            elapsed_time = datetime.now().timestamp() - start_time
            await asyncio.sleep(max(0, interval - elapsed_time))

    except WebSocketDisconnect:
        logger.info("클라이언트가 프레스 insert 웹소켓 연결을 끊었습니다.")
        await websocket.close()
    except Exception as e:
        logger.error(f"예기치 못한 오류: {e}")
        await websocket.close()

# Press Select WebSocket
@router.websocket("/ws/realtime-press/select")
async def websocket_realtime_press_select(websocket: WebSocket):
    await websocket.accept()
    last_data_press = None

    try:
        while True:
            await asyncio.sleep(1)

            if press_data != last_data_press:
                last_data_press = press_data

                async with press_lock:
                    if press_data is None or main.shared_trend_time_press is None:
                        await websocket.send_json({"message": "현재 trend_time이 없습니다. Insert가 실행 중인지 확인하십시오."})
                        continue

                    sample_press_data = [
                        float(press_data["pressure_1"]),
                        float(press_data["pressure_2"]),
                    ]
                    press_payload = {"data": sample_press_data}
                    async with aiohttp.ClientSession() as session:
                        async with session.post(NGROK_PRESS_MODEL_API, json=press_payload) as response:
                            if response.status == 200:
                                press_prediction_result = await response.json()
                                prediction = press_prediction_result.get("prediction")

                                conn = await get_db_press_connection()
                                async with conn.cursor() as cursor:
                                    insert_query = """
                                        INSERT INTO PRESS_SELECT_TREND (trend_time, prediction)
                                        VALUES (%s, %s)
                                    """
                                    await cursor.execute(insert_query, (main.shared_trend_time_press, prediction))
                                    await conn.commit()

                                logger.info(f"프레스 예측 값 - trend_time: {main.shared_trend_time_press}, 예측: {prediction}")
                                await websocket.send_json({"press_prediction": prediction})
                            else:
                                await websocket.send_json({"message": f"예측 API가 상태 {response.status}로 실패했습니다."})
    except WebSocketDisconnect:
        logger.info("클라이언트가 프레스 select 웹소켓 연결을 끊었습니다.")
        await websocket.close()
    except Exception as e:
        logger.error(f"예기치 못한 오류: {e}")
        await websocket.close()
