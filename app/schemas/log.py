from datetime import datetime
from pydantic import BaseModel,ConfigDict

class AccessLogResponse(BaseModel):
    id:int
    user_id:int | None
    file_id:int | None
    action:str
    status:str
    ip_address:str | None
    details:str | None
    timestamp:datetime

    model_config = ConfigDict(from_attributes=True)