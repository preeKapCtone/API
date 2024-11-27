from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI
import re
import os
from dotenv import load_dotenv
import time
import requests

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
    allow_origins=["*"],  # React 클라이언트 주소
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
    sentiment: str
    sentiment_score: float
    sentiment_magnitude: float

# OpenAI 클라이언트 생성
try:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise OpenAIInitializationError()  # 사용자 정의 예외 발생
    client = OpenAI(api_key=openai_api_key)
except Exception as e:
    raise OpenAIInitializationError()

# Google API 키 확인
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise RuntimeError("Google Cloud API 키가 .env에 없습니다.")

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

# 감정 분석 함수
def analyze_sentiment(text: str):
    try:
        url = f"https://language.googleapis.com/v1/documents:analyzeSentiment?key={google_api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "document": {
                "type": "PLAIN_TEXT",
                "content": text,
            },
            "encodingType": "UTF8",
        }
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        sentiment = response.json().get("documentSentiment", {})
        sentiment_score = sentiment.get("score", 0.0)
        sentiment_magnitude = sentiment.get("magnitude", 0.0)

        # 감정 상태 반환
        if sentiment_score > 0.5:
            sentiment_label = "긍정적"
        elif sentiment_score < -0.5:
            sentiment_label = "부정적"
        else:
            sentiment_label = "중립적"

        return sentiment_label, sentiment_score, sentiment_magnitude
    except Exception as e:
        raise RuntimeError(f"감정 분석 중 오류 발생: {e}")

# /api/posts 엔드포인트 정의
@app.post("/fastapi/posts", response_model=ChatResponse)
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

        # 감정 분석 수행
        sentiment, sentiment_score, sentiment_magnitude = analyze_sentiment(request.user_message)

        return ChatResponse(
            response=clean_text,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            sentiment_magnitude=sentiment_magnitude,
        )

    except BaseCustomException as e:
        raise e  # 사용자 정의 예외가 발생하면 전역 예외 핸들러에서 처리
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"서버 내부 오류: {e}")

