from pydantic import UUID4, BaseModel


class TokenPayload(BaseModel):
    sub: UUID4
    jti: UUID4
    iat: int
    exp: int
    nbf: int
    type: str
    roles: list[str] = []
