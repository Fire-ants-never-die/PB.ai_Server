# 🚀 PB.ai Server - Render 배포 가이드

## 📋 목차

1. [사전 준비](#사전-준비)
2. [GitHub 저장소 준비](#github-저장소-준비)
3. [Render 계정 생성 및 배포](#render-계정-생성-및-배포)
4. [환경 변수 설정](#환경-변수-설정)
5. [배포 확인 및 테스트](#배포-확인-및-테스트)
6. [문제 해결](#문제-해결)
7. [배포 후 관리](#배포-후-관리)

---

## 사전 준비

### ✅ 체크리스트

- [X] OpenAI API 키 발급 완료
- [X] GitHub 계정 준비
- [X] 로컬에서 서버 정상 동작 확인
- [X] 모든 테스트 통과 확인

### 📦 필요한 파일

다음 파일들이 프로젝트에 있는지 확인:

```
✅ requirements.txt      # Python 패키지 목록
✅ .gitignore           # Git에서 제외할 파일
✅ render.yaml          # Render 설정 (선택)
✅ main.py              # FastAPI 앱
✅ .env.example         # 환경 변수 예시
```

---

## GitHub 저장소 준비

### 1단계: .env 파일 제외 확인

**.gitignore**가 `.env` 파일을 제외하는지 확인:

```bash
cat .gitignore | grep ".env"
```

⚠️ **중요**: `.env` 파일은 절대 Git에 커밋하지 마세요!

### 2단계: Git 커밋 및 푸시

```bash
cd /Applications/Github/PB.ai_Server

# 상태 확인
git status

# 변경사항 추가
git add .

# 커밋
git commit -m "feat: Render 배포 준비

- requirements.txt 추가
- render.yaml 설정 파일 추가
- .gitignore 업데이트
- 로컬 테스트 완료
"

# GitHub에 푸시 (브랜치 확인)
git push origin main  # 또는 dev, master 등
```

### 3단계: GitHub 저장소 확인

GitHub에서 다음을 확인:

- ✅ `requirements.txt` 존재
- ✅ `main.py` 존재
- ✅ `.env` 파일이 **없음** (제외되었는지)
- ✅ 모든 코드 파일 업로드 완료

---

## Render 계정 생성 및 배포

### 1단계: Render 계정 생성

1. **Render 웹사이트** 접속

   ```
   https://render.com/
   ```
2. **Sign Up** 클릭

   - GitHub 계정으로 로그인 (권장)
   - 또는 이메일로 가입
3. GitHub 연동 허용

### 2단계: 새 Web Service 생성

1. **Dashboard** → **New +** → **Web Service** 클릭
2. **Connect GitHub Repository**

   - "Connect account" 클릭하여 GitHub 연동
   - 저장소 선택: `PB.ai_Server` (또는 실제 저장소명)
   - "Connect" 클릭
3. **Configure Service**

   ```
   Name: pb-ai-server (원하는 이름)
   Region: Singapore (또는 가까운 지역)
   Branch: main (또는 dev)
   Root Directory: (비워둠)
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
4. **Plan 선택**

   - **Free** 선택 (무료 플랜)
   - ⚠️ 무료 플랜 제한사항:
     - 15분 동안 요청이 없으면 자동 중지
     - 다시 시작 시 약 1분 소요
     - 월 750시간 무료
5. **Create Web Service** 클릭

### 3단계: 배포 시작

- Render가 자동으로 빌드 및 배포 시작
- **Logs** 탭에서 진행 상황 확인
- 약 5-10분 소요

---

## 환경 변수 설정

### 1단계: Environment Variables 설정

1. **Dashboard** → 생성한 서비스 클릭
2. **Environment** 탭 클릭
3. **Add Environment Variable** 클릭하여 추가:

#### 필수 환경 변수

```
Key: GPT_API_KEY
Value: sk-proj-실제_OpenAI_API_키
```

#### 선택 환경 변수 (크롤러 사용 시)

```
Key: DART_API_KEY
Value: 실제_DART_API_키
```

4. **Save Changes** 클릭
5. 자동으로 재배포 시작

### 2단계: 환경 변수 확인

**Logs** 탭에서 확인:

```
INFO:     Application startup complete.
server start
```

---

## 배포 확인 및 테스트

### 1단계: 배포 URL 확인

1. **Dashboard**에서 배포 URL 확인:

   ```
   https://pb-ai-server.onrender.com
   ```
2. 브라우저에서 접속:

   ```
   https://pb-ai-server.onrender.com/docs
   ```

### 2단계: Swagger UI 테스트

1. **Swagger UI**에서 `/ask` 엔드포인트 테스트:

   ```json
   {
     "user_id": "test_user",
     "question": "안녕하세요!",
     "tab_name": "테스트",
     "company_name": "삼성전자"
   }
   ```
2. **Execute** 클릭
3. 응답 확인:

   ```json
   {
     "status": "200",
     "user_id": "test_user",
     "company_name": "삼성전자",
     "question": "안녕하세요!",
     "answer": "..."
   }
   ```

### 3단계: curl로 테스트

```bash
curl -X POST https://pb-ai-server.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "question": "유동비율이란?",
    "tab_name": "재무분석",
    "company_name": "삼성전자"
  }'
```

### 4단계: 프론트엔드 연동

`main.py`의 CORS 설정 확인:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "https://your-frontend-domain.com"  # 프론트엔드 도메인 추가
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 문제 해결

### 문제 1: 배포 실패 (Build Failed)

**증상**:

```
ERROR: Could not find a version that satisfies the requirement xxx
```

**해결**:

1. `requirements.txt` 확인
2. 패키지 버전 호환성 확인
3. 불필요한 패키지 제거

### 문제 2: 서버 시작 실패 (Application startup failed)

**증상**:

```
openAI연결 실패
```

**해결**:

1. **Environment Variables** 확인
2. `GPT_API_KEY` 값 확인
3. API 키 앞뒤 공백 제거
4. 재배포

### 문제 3: CORS 에러

**증상**:

```
Access to fetch has been blocked by CORS policy
```

**해결**:

1. `main.py`에서 CORS 설정 수정:

   ```python
   allow_origins=["*"]  # 모든 도메인 허용 (개발용)
   ```
2. 프로덕션에서는 특정 도메인만 허용:

   ```python
   allow_origins=["https://your-frontend.com"]
   ```
3. Git 커밋 및 푸시하여 재배포

### 문제 4: 서버가 자동으로 중지됨

**원인**: 무료 플랜은 15분 동안 요청이 없으면 중지됨

**해결 방법**:

1. **헬스체크 추가** (권장):

   `main.py`에 추가:

   ```python
   @app.get("/health")
   async def health_check():
       return {"status": "healthy"}
   ```
2. **외부 모니터링 서비스 사용**:

   - UptimeRobot (무료): https://uptimerobot.com/
   - 5분마다 `/health` 엔드포인트 호출
3. **유료 플랜 업그레이드**:

   - $7/월부터 시작
   - 24/7 항상 실행

### 문제 5: 데이터베이스 초기화

**증상**: 배포 시마다 데이터가 사라짐

**원인**: 무료 플랜은 디스크가 임시 스토리지

**해결**:

1. **Render Disk** 추가 (유료)
2. **외부 데이터베이스 사용**:
   - PostgreSQL (Render 제공)
   - MongoDB Atlas (무료)
   - Supabase (무료)

---

## 배포 후 관리

### 로그 확인

1. **Render Dashboard** → 서비스 클릭
2. **Logs** 탭에서 실시간 로그 확인
3. 에러 발생 시 즉시 확인 가능

### 자동 배포 설정

1. **Settings** → **Build & Deploy**
2. **Auto-Deploy** 활성화
3. GitHub에 push하면 자동으로 재배포

### 배포 히스토리

1. **Events** 탭에서 배포 히스토리 확인
2. 이전 버전으로 롤백 가능

### 성능 모니터링

1. **Metrics** 탭에서 확인:
   - CPU 사용률
   - 메모리 사용률
   - 응답 시간
   - 요청 수

### 도메인 설정 (선택)

1. **Settings** → **Custom Domain**
2. 자신의 도메인 추가
3. DNS 설정 따라하기

---

## 배포 체크리스트

### 배포 전

- [ ] 로컬에서 모든 테스트 통과
- [ ] `.env` 파일 Git에서 제외 확인
- [ ] `requirements.txt` 최신화
- [ ] CORS 설정 확인
- [ ] GitHub에 푸시 완료

### 배포 중

- [ ] Render 계정 생성
- [ ] GitHub 저장소 연결
- [ ] 환경 변수 설정 (GPT_API_KEY)
- [ ] 빌드 성공 확인

### 배포 후

- [ ] Swagger UI 접속 확인
- [ ] API 테스트 성공
- [ ] 로그 확인
- [ ] 프론트엔드 연동 테스트
- [ ] 헬스체크 설정 (선택)

---

## 유용한 링크

- **Render 공식 문서**: https://render.com/docs
- **FastAPI 배포 가이드**: https://fastapi.tiangolo.com/deployment/
- **무료 DB 옵션**:
  - PostgreSQL: https://render.com/docs/databases
  - MongoDB Atlas: https://www.mongodb.com/cloud/atlas
  - Supabase: https://supabase.com/

---

## 비용 (2024년 기준)

### 무료 플랜

- **가격**: $0/월
- **메모리**: 512MB RAM
- **CPU**: 0.1 CPU
- **스토리지**: 임시 (재시작 시 삭제)
- **제한**: 15분 비활성화 시 중지

### 유료 플랜 (추천)

- **Starter**: $7/월
  - 512MB RAM
  - 0.5 CPU
  - 항상 실행
  - 디스크 추가 가능

---

## 🎉 완료!

배포가 성공했다면 다음 URL로 접속:

```
https://your-service.onrender.com/docs
```

**축하합니다! 🎊 PB.ai Server가 전세계에 배포되었습니다!**

---

**작성일**: 2025-12-18
**플랫폼**: Render.com
**앱 타입**: FastAPI Web Service
