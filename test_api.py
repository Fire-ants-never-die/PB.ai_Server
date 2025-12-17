#!/usr/bin/env python3
"""
PB.ai Server API 테스트 스크립트
로컬 서버가 실행 중일 때 사용하세요.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_response(title, response):
    """응답을 예쁘게 출력"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print(response.text)
    print()

def test_ask():
    """AI 질의응답 테스트"""
    print("\n🤖 테스트 1: AI 질의응답")
    response = requests.post(
        f"{BASE_URL}/ask",
        json={
            "user_id": "test_user",
            "question": "유동비율이란 무엇인가요?",
            "tab_name": "재무분석",
            "company_name": "삼성전자"
        }
    )
    print_response("AI 질의응답 결과", response)
    return response.status_code == 200

def test_ask_multiple():
    """여러 질문 테스트"""
    print("\n🤖 테스트 2: 여러 질문 (대화 기록 테스트)")

    questions = [
        "부채비율은 어떻게 계산하나요?",
        "ROE는 무엇인가요?",
        "당기순이익이란?"
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n  질문 {i}: {question}")
        response = requests.post(
            f"{BASE_URL}/ask",
            json={
                "user_id": "test_user",
                "question": question,
                "tab_name": "재무분석",
                "company_name": "삼성전자"
            }
        )
        print(f"  응답: {response.status_code}")
        time.sleep(1)  # 서버 부하 방지

    return True

def test_get_qna_by_company():
    """회사별 질답 기록 조회 테스트"""
    print("\n📋 테스트 3: 회사별 질답 기록 조회")
    response = requests.post(
        f"{BASE_URL}/prevqna/company",
        json={
            "user_id": "test_user",
            "question": "",
            "tab_name": "재무분석",
            "company_name": "삼성전자"
        }
    )
    print_response("회사별 질답 기록", response)
    return response.status_code == 200

def test_get_all_sessions():
    """전체 세션 조회 테스트"""
    print("\n📚 테스트 4: 전체 세션 조회")
    response = requests.post(
        f"{BASE_URL}/prevqna/session",
        json={
            "user_id": "test_user",
            "question": "",
            "tab_name": "",
            "company_name": ""
        }
    )
    print_response("전체 세션", response)
    return response.status_code == 200

def test_delete_session():
    """세션 삭제 테스트"""
    print("\n🗑️  테스트 5: 세션 삭제")

    # 먼저 테스트용 질문 추가
    print("  먼저 테스트 세션 생성...")
    requests.post(
        f"{BASE_URL}/ask",
        json={
            "user_id": "delete_test_user",
            "question": "이 세션은 삭제될 예정입니다",
            "tab_name": "테스트",
            "company_name": "테스트회사"
        }
    )
    time.sleep(1)

    # 삭제
    print("  세션 삭제 중...")
    response = requests.post(
        f"{BASE_URL}/prevqna/delete",
        json={
            "user_id": "delete_test_user",
            "question": "",
            "tab_name": "테스트",
            "company_name": "테스트회사"
        }
    )
    print_response("세션 삭제 결과", response)

    # 삭제 확인
    print("  삭제 확인 중...")
    verify = requests.post(
        f"{BASE_URL}/prevqna/company",
        json={
            "user_id": "delete_test_user",
            "question": "",
            "tab_name": "테스트",
            "company_name": "테스트회사"
        }
    )
    print_response("삭제 확인 (size=0이어야 함)", verify)

    return response.status_code == 200

def test_multiple_users():
    """다중 사용자 테스트"""
    print("\n👥 테스트 6: 다중 사용자")

    users = [
        {"user_id": "user1", "company": "삼성전자"},
        {"user_id": "user2", "company": "SK하이닉스"},
        {"user_id": "user3", "company": "LG에너지솔루션"}
    ]

    for user in users:
        print(f"\n  {user['user_id']} -> {user['company']}")
        response = requests.post(
            f"{BASE_URL}/ask",
            json={
                "user_id": user["user_id"],
                "question": f"{user['company']}의 주가는?",
                "tab_name": "주식분석",
                "company_name": user["company"]
            }
        )
        print(f"  응답: {response.status_code}")
        time.sleep(1)

    return True

def test_server_health():
    """서버 상태 확인"""
    print("\n🏥 서버 상태 확인")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code == 200:
            print("✅ 서버가 정상적으로 실행 중입니다!")
            print(f"   Swagger UI: {BASE_URL}/docs")
            return True
        else:
            print(f"⚠️  서버 응답 이상: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다!")
        print("   다음 명령어로 서버를 시작하세요:")
        print("   uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

def main():
    """메인 테스트 실행"""
    print("\n" + "="*60)
    print("  PB.ai Server API 테스트 시작")
    print("="*60)

    # 서버 상태 확인
    if not test_server_health():
        print("\n❌ 서버가 실행되지 않았습니다. 테스트를 중단합니다.")
        return

    # 테스트 실행
    results = {
        "AI 질의응답": False,
        "여러 질문": False,
        "회사별 기록 조회": False,
        "전체 세션 조회": False,
        "세션 삭제": False,
        "다중 사용자": False
    }

    try:
        results["AI 질의응답"] = test_ask()
        results["여러 질문"] = test_ask_multiple()
        results["회사별 기록 조회"] = test_get_qna_by_company()
        results["전체 세션 조회"] = test_get_all_sessions()
        results["세션 삭제"] = test_delete_session()
        results["다중 사용자"] = test_multiple_users()

    except requests.exceptions.ConnectionError:
        print("\n❌ 서버 연결이 끊어졌습니다!")
    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {e}")

    # 결과 요약
    print("\n" + "="*60)
    print("  테스트 결과 요약")
    print("="*60)

    for test_name, result in results.items():
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{test_name:20s} : {status}")

    success_count = sum(results.values())
    total_count = len(results)

    print(f"\n총 {total_count}개 테스트 중 {success_count}개 성공")

    if success_count == total_count:
        print("\n🎉 모든 테스트를 통과했습니다!")
    else:
        print("\n⚠️  일부 테스트가 실패했습니다. 로그를 확인하세요.")

if __name__ == "__main__":
    main()
