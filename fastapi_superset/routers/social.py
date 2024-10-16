from fastapi import APIRouter

router = APIRouter()
@router.get("/")
async def management_home():
    return {"message": "Welcome to Social Home"}

@router.get("/keyword")
async def social_keyword():
    return {"message": "Social keyword data"}

@router.get("/np-ratio/all")
async def np_ratio_all():
    return {"message": "NP ratio for all"}

@router.get("/np-ratio/car")
async def np_ratio_car():
    return {"message": "NP ratio for car"}

@router.get("/np-ratio/journal")
async def np_ratio_journal():
    return {"message": "NP ratio for journal"}

@router.get("/count/journal")
async def journal_count():
    return {"message": "Journal count"}
