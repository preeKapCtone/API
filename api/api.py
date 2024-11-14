#시간 측정 전 코드

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import time
import re
import os

# OpenAI 클라이언트 생성 (실제 API 키로 대체하세요)
client = OpenAI(api_key="API key")

app = FastAPI()

# CORS 설정 추가 (React 클라이언트에서 서버 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 클라이언트 주소
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 데이터 모델 정의
class ChatRequest(BaseModel):
    user_message: str
    assistant_id: str

# 응답 데이터 모델 정의 (응답 메시지와 응답 시간 포함)
class ChatResponse(BaseModel):
    response: str
    response_time: float  # 응답 시간 추가

# Run의 상태를 체크하여 완료될 때까지 대기
def wait_on_run(run, thread):
    while run.status in ["queued", "in_progress"]:
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

# /chat 엔드포인트 정의 (응답 시간 측정 포함)
@app.post("/api/posts", response_model=ChatResponse)
async def chat_with_assistant(request: ChatRequest):
    try:
        # Assistant ID로 Assistant 객체 가져오기
        assistant = client.beta.assistants.retrieve(request.assistant_id)

        # 새로운 대화 스레드 생성
        thread = client.beta.threads.create()

        # 사용자 메시지를 스레드에 추가
        user_message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role='user',
            content=request.user_message
        )

        # Run 생성 및 Assistant 응답 생성 시작
        start_time = time.time()  # 응답 시간 측정 시작
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        # Run이 완료될 때까지 대기
        wait_on_run(run, thread)

        # 완료 시점의 시간 기록
        end_time = time.time()
        response_time = end_time - start_time  # 응답 시간 계산 (초 단위)

        # 사용자 메시지 이후의 Assistant 응답 메시지 가져오기
        messages = client.beta.threads.messages.list(
            thread_id=thread.id, order="asc", after=user_message.id
        )

        # 응답 텍스트 추출 및 정제
        response_text = ""
        for message in messages:
            for c in message.content:
                response_text += c.text.value

        clean_text = re.sub('【.*?】', '', response_text)  # 불필요한 텍스트 제거
        return ChatResponse(response=clean_text, response_time=response_time)

    except Exception as e:
        print("Detailed Error:", e)  # 오류 로그 출력
        raise HTTPException(status_code=500, detail=str(e))




