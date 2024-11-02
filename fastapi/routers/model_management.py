from fastapi import APIRouter, HTTPException, UploadFile, Form, File
from database import get_db_connection
from typing import Optional, List
from pydantic import BaseModel
from urllib.parse import unquote

router = APIRouter()

# ====================================
# 데이터 모델 정의
# ====================================
class ModelData(BaseModel):
    model_name: str
    model_version: str
    python_version: str
    library: str
    model_type: str
    loss: float
    accuracy: float
    deployment_date: str

# ====================================
# 기본 관리 엔드포인트
# ====================================
@router.get("/")
async def management_home():
    return {"message": "Welcome to Model Management Home"}

# ====================================
# 모델 정보 조회 엔드포인트
# ====================================
@router.get("/model-select")
async def get_model_info():
    """전체 모델 정보 목록 가져오기"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT model_info_id, model_name, model_version, python_version, library, model_type, loss, accuracy, deployment_date "
                "FROM model_info"
            )
            result = await cursor.fetchall()
            conn.close()

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
                    "deployment_date": row[8]
                } for row in result
            ] if result else []

            return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/model-info/{model_id}")
async def get_model_info_by_id(model_id: str):
    try:
        # 모델 ID 디코딩 처리
        model_id = unquote(model_id)

        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT model_name, model_version, python_version, library, model_type, loss, accuracy, deployment_date "
                "FROM model_info WHERE model_info_id = %s", (model_id,)
            )
            result = await cursor.fetchone()
            conn.close()

            if result:
                # 모델 이름에 따라 프로세스 이름 결정
                model_name = result[0]
                if 'press' in model_name.lower():
                    process_name = 'press'
                elif 'welding' in model_name.lower():
                    process_name = 'welding'
                else:
                    process_name = 'unknown'

                return {
                    "model_name": model_name,
                    "model_version": result[1],
                    "python_version": result[2],
                    "library": result[3],
                    "model_type": result[4],
                    "loss": result[5],
                    "accuracy": result[6],
                    "deployment_date": result[7],
                    "process_name": process_name  # 프로세스 이름 추가
                }
            else:
                raise HTTPException(status_code=404, detail="Model not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-avg-accuracy")
async def get_model_avg_accuracy():
    """최근 3개 모델의 평균 정확도 가져오기"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                """SELECT model_name, accuracy 
                    FROM model_info
                    ORDER BY deployment_date DESC 
                    LIMIT 3"""
            )
            result = await cursor.fetchall()
            conn.close()

            models = [
                {
                    "model_name": row[0],
                    "accuracy": row[1]
                } for row in result
            ] if result else []

            return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-avg-loss")
async def get_model_avg_loss():
    """최근 3개 모델의 평균 손실 값 가져오기"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                """SELECT model_name, loss 
                    FROM model_info
                    ORDER BY deployment_date DESC 
                    LIMIT 3"""

            )
            result = await cursor.fetchall()
            conn.close()

            models = [
                {
                    "model_name": row[0],
                    "loss": row[1]
                } for row in result
            ] if result else []

            return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
