# M3-ROBERTA-003 검토 (551cbf3)
1. Validation 누수: OK — Training/TL_서울_구급.zip만 읽음(prepare_rows), 공식 Val 경로 없음
2. 분할 누수: OK — 80:20 다중라벨 층화 분할, call_id 중복 행 거부 및 train/holdout call_id 교집합 검사(prepare_split)
3. 입력 화이트리스트: OK — utterances[].text만 사용, 라벨 JSON은 타깃 용도로만
4. M2 독립성: 해당 없음(M3)
5. 외부 데이터/네트워크/비밀: OK — 고정 revision 공개 모델을 DCC_RUN_ROOT/models에 다운로드(허용), 비밀 접근 없음
9. requirements.txt: 변경 없음
6. 실행 계약: OK — metrics.json/best.ckpt 작성, seed별 metrics 건너뛰기, epoch별 ckpt_last 원자 저장·복원(옵티마이저/스케줄러/RNG 포함)
7. 명세 일치: OK — BCE(pos_weight 0.5/cap 6, train만) + 1.0*(1-mean softF1), fp32 마이크로배치(8)×2 누적=16, lr 1e-5, warmup 10%, 3 epoch, thr>=0.5, 후처리 없음, command 일치
8. 버그: 특이사항 없음 — 최종 epoch 3 점수, 선택 없음, 시드 고정
[MINOR] soft-F1은 마이크로배치 8 단위로 계산됨(명세의 "미니배치"와 해석 차이 가능, 기록됨 config.soft_f1_batch_size)
VERDICT: PASS
