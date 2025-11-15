from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


@router.get("/hello", tags=["greetings"])
def say_hello(name: str = "World"):
    return {"message": f"Hello, {name}!"}
