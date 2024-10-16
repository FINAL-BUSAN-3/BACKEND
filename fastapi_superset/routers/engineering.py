from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def management_home():
    return {"message": "Welcome to Engineering Home"}

@router.get("/press")
async def management_home():
    return {"message": "Welcome to Engineering Press Home"}

@router.get("/welding")
async def management_home():
    return {"message": "Welcome to Engineering Welding Home"}

@router.get("/realtime-press/select")
async def realtime_press_select():
    return {"message": "Realtime press select"}

@router.get("/realtime-press/insert")
async def realtime_press_insert():
    return {"message": "Realtime press insert"}

@router.get("/realtime-welding/select")
async def realtime_welding_select():
    return {"message": "Realtime welding select"}

@router.get("/realtime-welding/insert")
async def realtime_welding_insert():
    return {"message": "Realtime welding insert"}

@router.get("/realtime-press/trend")
async def realtime_press_trend():
    return {"message": "Press trend data"}

@router.get("/realtime-welding/trend")
async def realtime_welding_trend():
    return {"message": "Welding trend data"}
