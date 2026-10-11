# M3-KCBERT-CORR-001 PR #155 (f7bade8) 검토

작성자는 팀원(subin050203-prog)이며 Codex lab PR이 아니다. 읽기 전용으로 검토했다.

1. Validation 누수: OK. 공식 Validation은 열지 않고 Training 서울 구급 zip만 읽음 (`prepare_rows`). 가중치는 train 분할만으로 계산 (`weights`).
2. 분할 누수: OK. `prepare_split`이 call_id 중복 행을 거부하고 train/holdout call_id 교집합을 검사.
3. 입력 화이트리스트: OK. 입력은 utterances의 text만(`transcript`). `symptom`은 정답 라벨로만 사용.
4. M2 발화 독립성: 해당 없음(M3).
5. 외부 데이터·네트워크·비밀: OK. 고정 revision 모델만 `$DCC_RUN_ROOT/models`에 내려받음. 토큰·비밀 접근 없음.
9. requirements.txt: OK. 변경 없음.
6. 실행 계약: OK. `metrics.json`·`best.ckpt` 작성, `ckpt_last.pt`로 epoch 단위 재개, seed별 결과 재사용.
7. 명세 일치: PLCP/CLCP 보조 손실(각 0.2)은 학습 전용 헤드에만 쓰이고, 추론은 기존 9 logits만 사용. 정답 라벨은 보조 헤드에만 전달되며 smoke에서 가려진 라벨 비누출을 검사. threshold `>= 0.5`, 후처리 없음.
8. 명백한 버그: 없음.

- [MINOR] scripts/lab/m3-kcbert-corr-001.py:4 — 모듈 docstring에 리터럴 `\n`이 남아 있음 — 개행으로 수정.
- [MINOR] scripts/lab/m3-kcbert-corr-001.py:28 — `REVISION = "0f2f3f8"` 단축 해시 — 전체 40자 해시로 고정하면 다운로드 실패 위험이 줄어듦.
- [MINOR] 분할이 KCBERT-012와 동일하다는 주장은 자체 `rows.json` 순서와 seed 42에 의존함 — 실행 시 `val_files.txt`를 KCBERT-012와 대조해 확인.

참고: `specs/M3-KCBERT-CORR-001.json`과 승인된 proposal 이슈가 없고, PR 본문에 `COMMAND:` 줄이 없으며 PR 본문이 승인·제출 사용 금지를 명시했다. 코드 자체는 문제가 없으므로 PASS이나 큐에 제출하지 않았다.

VERDICT: PASS
