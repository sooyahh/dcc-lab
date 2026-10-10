# M1-HEAD-001 검토 (PR #136, 1aef54a)

1. Validation 누수: OK — 공식 Val 경로 없음. `training_metadata`는 Training zip만 읽음 (m1-head-001.py:78-80). StandardScaler는 fold/train 파이프라인 안에서만 fit.
2. 분할 누수: OK — 캐시 split을 seed-42 층화 분할과 대조(:223), call_id 교집합 검사(:225). C는 train 안 5-fold CV로만 선택(:116-131), holdout 미사용.
3. 입력 필드: OK — 캐시 52D+512D 음향 특징만 사용. 성별은 정답으로만.
4. M2 독립성: 해당 없음.
5. 외부 데이터/네트워크/비밀: OK — 다운로드·API·토큰 접근 없음. 쓰기는 LAB_OUT/LAB_WORK 한정.
9. requirements.txt: OK — 변경 없음.
6. 실행 계약: OK — metrics.json, best.ckpt 작성. CV fold·헤드 ckpt·holdout 결과 단계별 재개. 캐시 크기·연속성·분할 검증 후 불일치 시 즉시 실패. 행 식별 해시는 baseline(m1-xvec-001.py:206-207)과 동일 구조(wav/json 경로가 work 기준 상대 경로)로 일치.
7. 명세 일치: OK — (b)LR 재현, (e)RBF-SVC C∈{0.3,1,3}, (f)HGB, (g)MLP, McNemar 정확검정, 오답 겹침, 길이 구간, 시간 기록, holdout_probs.npy/columns/val_files.txt 구현. command 인자 일치.
8. 버그: OK — 오답 겹침 매핑(b_only/e_only), McNemar 칸, 동률 시 작은 C 선택 확인. JSON 직렬화 타입 이상 없음.

MINOR: 위 외 없음 (런타임 의존성은 Colab에서 확인됨, 로컬 numpy 미설치로 smoke만 수행).

VERDICT: PASS
