# M3-KCBERT-002 실행 전 검토 (PR #68, b5744de)

1. Validation 누수: OK — 공식 Validation 접근 없음
2. 분할 누수: OK — P0 `_make_split(seed=42)`, 23,408/5,792, stem 교집합 검사
3. 입력 필드: OK — 전사 text만
4. M2 발화 독립성: 해당 없음
5. 외부 데이터·네트워크·비밀: OK — 고정 revision 다운로드 후 local_files_only
9. requirements.txt: 변경 없음
6. 실행 계약: 재개·metrics.json OK. 라벨 입력이 현재 Drive 구조와 불일치(아래 MAJOR)
7. 명세 일치: 학습 로직 OK
8. 명백한 버그: 학습 로직 없음

## 문제
[심각도: MAJOR] scripts/lab/m3-kcbert-002.py:79-86 (`stage_labels`) — 7143ad8 지적과 1차 Colab 실패의 원인이 그대로다. 이번 커밋(7143ad8→b5744de)은 완료 seed 검증·메모리 정리만 추가했고 `Training/TL_서울_구급.zip`이 없으면 여전히 `ValueError`로 즉시 종료한다. Drive에는 압축 해제된 JSON 29,200건뿐이므로 같은 실패가 재발한다. smoke(327-337행)도 zip 구조만 검증해 이를 못 잡는다. 고칠 방법: zip이 없으면 `Training` 아래 `TL_서울_구급` 라벨 JSON을 한 번 읽어 `LAB_WORK`에 단일 캐시(zip/jsonl)로 묶고 재개 시 재사용하며, `p0.load_training_dataframe`가 읽을 수 있는 형태로 넘긴다. smoke도 압축 해제 구조로 검증.
[심각도: MINOR] :26 — REVISION이 7자 단축 해시(`0f2f3f8`). 전체 40자 커밋 해시로 고정 권장
[심각도: MINOR] seed별 ckpt(~1.3GB)를 LAB_OUT(Drive)에 저장 — 용량 부담

VERDICT: FAIL
