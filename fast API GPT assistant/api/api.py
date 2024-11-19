from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI
import requests
import re
import os
from dotenv import load_dotenv
import time

# .env 파일 로드
load_dotenv()


# 사용자 정의 예외의 기본 클래스
class BaseCustomException(Exception):
    """Base class for custom exceptions"""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

    def __str__(self):
        return self.detail

# 사용자 정의 예외: OpenAI 초기화 오류
class OpenAIInitializationError(BaseCustomException):
    def __init__(self):
        super().__init__(status_code=500, detail="OpenAI 클라이언트 초기화 오류")

# 사용자 정의 예외: CLOVA API 오류
class ClovaAPIError(BaseCustomException):
    def __init__(self, message: str):
        super().__init__(status_code=500, detail=f"CLOVA Sentiment API 호출 오류: {message}")

# 사용자 정의 예외 핸들러
async def base_custom_exception_handler(request: Request, exc: BaseCustomException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

# FastAPI 앱 초기화
app = FastAPI()

# 사용자 정의 예외 핸들러 등록
app.add_exception_handler(BaseCustomException, base_custom_exception_handler)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React 클라이언트 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 데이터 모델
class ChatRequest(BaseModel):
    user_message: str
    assistant_id: str

# 응답 데이터 모델
class ChatResponse(BaseModel):
    response: str
    sentiment: str  # 감정 결과

# OpenAI 클라이언트 생성
try:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise OpenAIInitializationError()  # 사용자 정의 예외 발생
    client = OpenAI(api_key=openai_api_key)
except Exception as e:
    raise OpenAIInitializationError()

# Run 상태 확인 함수
def wait_on_run(run, thread):
    try:
        while run.status in ["queued", "in_progress"]:
            run = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id,
            )
            time.sleep(0.5)
        return run
    except Exception as e:
        raise RuntimeError(f"Run 상태 확인 중 오류 발생: {e}")

# CLOVA Sentiment API 호출 함수
def analyze_sentiment(text):
    try:
        CLOVA_SENTIMENT_URL = "https://naveropenapi.apigw.ntruss.com/sentiment-analysis/v1/analyze"
        clova_client_id = os.getenv("CLOVA_CLIENT_ID")
        clova_api_key = os.getenv("CLOVA_API_KEY")

        if not clova_client_id or not clova_api_key:
            raise ClovaAPIError("CLOVA API 키 또는 클라이언트 ID가 설정되지 않았습니다.")

        headers = {
            "X-NCP-APIGW-API-KEY-ID": clova_client_id,
            "X-NCP-APIGW-API-KEY": clova_api_key,
            "Content-Type": "application/json",
        }
        response = requests.post(
            CLOVA_SENTIMENT_URL,
            json={"content": text},
            headers=headers
        )
        response.raise_for_status()
        return response.json()["document"]["sentiment"]
    except requests.exceptions.RequestException as e:
        raise ClovaAPIError(str(e))  # 사용자 정의 예외 발생

# /api/posts 엔드포인트 정의
@app.post("/api/posts", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    try:
        # OpenAI Assistant 처리
        assistant = client.beta.assistants.retrieve(request.assistant_id)
        thread = client.beta.threads.create()
        user_message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role='user',
            content=request.user_message
        )
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )
        wait_on_run(run, thread)
        messages = client.beta.threads.messages.list(
            thread_id=thread.id, order="asc", after=user_message.id
        )

        # 응답 텍스트 추출 및 정제
        response_text = ""
        for message in messages:
            for c in message.content:
                response_text += c.text.value
        clean_text = re.sub('【.*?】', '', response_text)

        # CLOVA Sentiment API 호출
        sentiment = analyze_sentiment(clean_text)

        return ChatResponse(response=clean_text, sentiment=sentiment)

    except BaseCustomException as e:
        raise e  # 사용자 정의 예외가 발생하면 전역 예외 핸들러에서 처리
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {e}")


