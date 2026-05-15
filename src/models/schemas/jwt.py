import datetime

import pydantic


class JWToken(pydantic.BaseModel):
    exp: datetime.datetime
    sub: str
    jti: str


class JWTUser(pydantic.BaseModel):
    user_id: str
    username: str
