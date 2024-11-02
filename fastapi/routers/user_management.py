from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from database import get_db_connection
import pytz

router = APIRouter()

# ====================================
# 데이터 모델 정의
# ====================================
class User(BaseModel):
    name: str
    employeeNo: int
    position: str

class Group(BaseModel):
    group_name: str
    description: str

class UpdateUser(BaseModel):
    id: int
    position: str

# ====================================
# 사용자 관리 기본 엔드포인트
# ====================================
@router.get("/")
async def management_home():
    return {"message": "Welcome to User Management Home"}

@router.get("/user")
async def user():
    return {"message": "User data"}

@router.get("/user-detail")
async def user_detail():
    return {"message": "User detail"}

@router.get("/user-save")
async def user_save():
    return {"message": "User saved"}

@router.get("/group")
async def group():
    return {"message": "Group data"}

# ====================================
# 사용자 정보 CRUD 엔드포인트
# ====================================
@router.get("/user-list")
async def get_employees():
    """전체 사용자 목록 가져오기"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT employees.name, employees.employee_no, employees.position, employees.last_login FROM employees"
            )
            result = await cursor.fetchall()
            conn.close()

            kst = pytz.timezone("Asia/Seoul")
            employees = [
                {
                    "id": row[1],
                    "name": row[0],
                    "employeeNo": row[1],
                    "position": row[2],
                    "lastLogin": row[3].astimezone(kst).isoformat() if row[3] else "최근 기록이 없음"
                }
                for row in result
            ]
            return {"employees": employees}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/user-add")
async def add_user(user: User):
    """새 사용자 추가"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM employees WHERE employee_no = %s", (user.employeeNo,))
            (count_employee,) = await cursor.fetchone()

            await cursor.execute("SELECT COUNT(*) FROM employees WHERE name = %s", (user.name,))
            (count_name,) = await cursor.fetchone()

            if count_employee > 0:
                raise HTTPException(status_code=400, detail="이미 존재하는 사번입니다.")
            if count_name > 0:
                raise HTTPException(status_code=400, detail="이미 존재하는 이름입니다.")

            await cursor.execute(
                "INSERT INTO employees (name, employee_no, position, last_login) VALUES (%s, %s, %s, NULL)",
                (user.name, user.employeeNo, user.position)
            )
            await conn.commit()
        conn.close()
        return {"message": "사용자가 성공적으로 추가되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/user-detail/{user_id}")
async def update_user_detail(user_id: int, user: UpdateUser):
    """사용자 정보 업데이트"""
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

@router.delete("/user-delete/{employee_no}")
async def delete_user(employee_no: int):
    """사용자 삭제"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM employees WHERE employee_no = %s", (employee_no,))
            await conn.commit()
        conn.close()
        return {"message": "사용자가 성공적으로 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ====================================
# 그룹 관리 CRUD 엔드포인트
# ====================================
@router.get("/group-list")
async def get_user_groups():
    """전체 그룹 목록 가져오기"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT id, group_name, description FROM user_groups")
            user_groups = await cursor.fetchall()
        conn.close()
        return {"user_groups": user_groups}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/group-add")
async def add_group(group: Group):
    """새 그룹 추가"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "INSERT INTO user_groups (group_name, description) VALUES (%s, %s)",
                (group.group_name, group.description)
            )
            await conn.commit()
        conn.close()
        return {"message": "권한이 성공적으로 추가되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/group-delete/{group_id}")
async def delete_group(group_id: int):
    """그룹 삭제"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute("DELETE FROM user_groups WHERE id = %s", (group_id,))
            await conn.commit()
        conn.close()
        return {"message": "권한이 성공적으로 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user-detail/{user_id}")
async def get_user_detail(user_id: int):
    """단일 사용자 정보 조회"""
    try:
        conn = await get_db_connection()
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT name, employee_no, position, last_login FROM employees WHERE employee_no = %s", (user_id,)
            )
            user_result = await cursor.fetchone()
            if not user_result:
                raise HTTPException(status_code=404, detail="User not found")

            user = {
                "name": user_result[0],
                "employeeNo": user_result[1],
                "position": user_result[2],
                "lastLogin": user_result[3],
                "roles": user_result[2].split(';') if user_result[2] else []
            }
        conn.close()
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
