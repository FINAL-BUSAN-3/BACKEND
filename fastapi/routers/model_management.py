from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def management_home():
    return {"message": "Welcome to Model Management Home"}

@router.get("/model-select")
async def model_select():
    return {"message": "Model selection data"}

@router.get("/model-select/detail")
async def model_select_detail():
    return {"message": "Model detail data"}
