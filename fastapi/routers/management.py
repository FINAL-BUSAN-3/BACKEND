from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def management_home():
    return {"message": "Welcome to Management Home"}

@router.get("/stock")
async def management_stock():
    return {"message": "Stock management data"}

@router.get("/month-sales")
async def management_month_sales():
    return {"message": "Monthly sales data"}

@router.get("/press/{period}")
async def management_press(period: str):
    return {"message": f"Press data for {period}"}

@router.get("/welding/{period}")
async def management_welding(period: str):
    return {"message": f"Welding data for {period}"}
