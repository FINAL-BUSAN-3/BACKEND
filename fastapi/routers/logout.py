from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def management_home():
    return {"message": "Welcome to User Logout Home"}
