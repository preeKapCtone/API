클론 후 해야 할 일.

0. python 3.11.0 설치
- 방법은 맥이랑 윈도우 각자 다르니 알아서 설치해주세요
(**환경변수 설정은 필수입니다.**)
(웬만해서 brew install 하든 윈도우에서 그냥 깔든 다 저절로 설정될거에용)

1.Poetry 설치
윈도우 기준 - Powershell
```
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

설치 후 Poetry의 경로를 시스템 환경 변수에 추가해주면, 어디서든 poetry 명령을 사용할 수 있습니다. 환경 변수 경로 추가가 어려운 경우, 재부팅 후 사용이 가능할 수 있습니다.

맥 기준
```
curl -sSL https://install.python-poetry.org | python3 -
```
Poetry는 기본적으로 ~/.local/bin에 설치되므로, 이 경로를 PATH 환경 변수에 추가

~/.zshrc나 ~/.bashrc 파일에 다음을 추가
```
export PATH="$HOME/.local/bin:$PATH"
```

설치 확인 코드
```
poetry --version
```

2. 파이썬 의존성 설치
```
 poetry install --no-root
```


3. 가상환경 생성
```
fast API GPT assistant git:(main) ✗ python3 -m venv .venv
```
윈도우
```
python -m venv .venv
```
(경로는 똑같아야 합니다.)

가상환경 활성화
cmd
```
.venv\Scripts\activate
```
Powershell
```
.venv\Scripts\Activate.ps1
```
mac
```
source .venv/bin/activate
```
가상환경 비활성화 코드
```
deactivate

```

4. 모듈 설치 (가상환경이 켜져있는 상태여야합니다.)
```
pip install -r requirements.txt
```

만약 안될 경우
```
pip install openai
pip install python-dotenv
혹은 그외 다른 패키지 보고 설치 요망
```

5. .env 환경변수 (가상환경이 꺼져있는상태여야함)
윈도우에서 생성

(cmd)
```
echo. > .env
```
(Powershell)
```
New-Item -Path . -Name ".env" -ItemType "file"
```

mac에서 생성
```
touch .env
```

**주의 ! .env.txt아닙니다 그냥 .env 파일형태여야합니다**

그 후, Notion에 있는 API키 집어넣기.

6. 실행 

실행할땐 가상환경켜져있는 상태에서 실행하는게 좋긴하다만 
굳이 안켜도 동작은 합니다. 둘다 상관은 없어요.

```
poetry run uvicorn api.api:app --reload

```




