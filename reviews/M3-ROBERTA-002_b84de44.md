# M3-ROBERTA-002 검토 (b84de44)

1. Validation 누수: OK — Training/TL_서울_구급.zip만 읽음(m3-roberta-002.py:100), 공식 Val 경로 없음, 명세 uses_official_val=false 일치
2. 분할 누수: OK — 고유 call_id 검증(:124), MultilabelStratifiedShuffleSplit seed 42(KCBERT-003/005와 동일), call_id 교집합 검사(:147). pos_weight는 train 분할 라벨에서만 계산(:348)
3. 입력 필드: OK — utterances[].text만 사용(:70-73), symptom은 타깃으로만 사용
4. M2 독립성: 해당 없음(M3)
5. 외부 데이터·네트워크: OK — ROBERTA-001과 같은 고정 revision 28d9112(001 검토에서 HF API로 확인)를 DCC_RUN_ROOT/models/roberta-large에 받고 마커로 revision 검증, 이후 local_files_only. 비밀 접근 없음
9. requirements.txt: OK — 변경 없음 (iterative-stratification은 기존 항목)
6. 실행 계약: OK — metrics.json 작성, epoch마다 ckpt_last 원자 저장(optimizer/scheduler/scaler/RNG), seed 완료 시 건너뜀, ckpt_last는 seed 필드로 구분, main() 초반 모델 준비로 조기 실패
7. 명세 일치: OK — pos_weight=clip(0.5*sqrt(neg/pos),1,6), lr 1e-5, warmup 10%, wd 0.01, fp16, 실효 batch 16(2×8), 256토큰, 3 epoch, seed 42/43/44, thr 0.5. COMMAND가 argparse(--out)와 일치
8. 명백한 버그: 없음 — 마이크로배치 손실 스케일링, grad clip 1.0, scaler skip 시 scheduler 미진행 처리 정상

- [MINOR] — seed별 best.ckpt(약 1.3GB)×3 + 대표본 → Drive 약 5GB
- [MINOR] — micro-batch 2 + gradient checkpointing으로 001보다 느릴 수 있음(예산 5h 내 여부 실행 시 확인)

VERDICT: PASS
