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
    return {"message": "Welcome to Model Deployment Home"}

@router.get("/process-select")
async def process_select():
    return {"message": "Process selection"}

@router.get("/model-insert")
async def model_insert():
    return {"message": "Model inserted"}

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
                "SELECT model_info_id, model_name, model_version, python_version, library, model_type, loss, accuracy "
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


@router.get("/model-detail")
async def get_active_model_info():
    """활성 모델 정보 가져오기"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT model_use_id FROM model_use WHERE model_use_state = 1 LIMIT 1")
            result = await cursor.fetchone()

            if not result:
                raise HTTPException(status_code=404, detail="No active model found")

            model_info_id = result[0]
            await cursor.execute("""
                SELECT model_name, model_version, python_version, library, model_type, loss, accuracy
                FROM model_info WHERE model_info_id = %s
            """, (model_info_id,))
            model_info = await cursor.fetchone()
            conn.close()

            if not model_info:
                raise HTTPException(status_code=404, detail="Model information not found")

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

# ====================================
# 모델 배포 및 적용 엔드포인트
# ====================================
@router.post("/deploy-previous-model")
async def deploy_previous_model(model_info_id: str, deployment_date: str):
    """이전 모델 배포"""
    conn = await get_db_connection()
    async with conn.cursor() as cursor:
        try:
            await cursor.execute(
                "UPDATE model_info SET deployment_date = %s WHERE model_info_id = %s",
                (deployment_date, model_info_id)
            )
            await cursor.execute("UPDATE model_use SET model_use_state = 0")
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

@router.post("/model-apply")
async def model_apply(
    model_name: str = Form(...),
    model_version: str = Form(...),
    python_version: str = Form(...),
    library: str = Form(...),
    deployment_date: str = Form(...),
    model_type: str = Form(...),
    loss: float = Form(...),
    accuracy: float = Form(...),
    file: Optional[UploadFile] = File(None)
):
    """새 모델 적용 및 MySQL에 저장"""
    conn = await get_db_connection()
    async with conn.cursor() as cursor:
        try:
            file_content = await file.read() if file else None
            date_part = deployment_date[2:10]
            time_part = deployment_date[11:16].replace(":", "-")
            model_info_id = f"{model_name}-{date_part}-{time_part}"

            insert_model_info = """
                INSERT INTO model_info 
                (model_info_id, model_name, model_version, python_version, library, model_type, deployment_date, loss, accuracy, model_info_file)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            await cursor.execute(insert_model_info, (
                model_info_id, model_name, model_version, python_version, library, model_type, deployment_date, loss, accuracy, file_content
            ))

            await cursor.execute("UPDATE model_use SET model_use_state = 0")
            insert_model_use = """
                INSERT INTO model_use 
                (model_use_id, model_use_state, model_use_file) 
                VALUES (%s, %s, %s)
            """
            await cursor.execute(insert_model_use, (model_info_id, 1, file_content))
            await conn.commit()

            return {
                "message": "데이터가 MySQL에 성공적으로 저장되었습니다.",
                "model_info_id": model_info_id,
                "file_uploaded": bool(file)
            }
        except Exception as e:
            await conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            conn.close()
