from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def management_home():
    return {"message": "Welcome to Model Deployment Home"}

@router.get("/process-select")
async def process_select():
    return {"message": "Process selection"}

@router.get("/model-insert")
async def model_insert():
    return {"message": "Model inserted"}

# @router.get("/model-select")
# async def model_select():
#     return {"message": "Model selected"}

@router.get("/model-detail")
async def model_detail():
    return {"message": "Model detail"}

@router.get("/model-apply")
async def model_apply():
    return {"message": "Model applied"}
