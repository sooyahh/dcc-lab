VERDICT: 재시도
실행 문제: exit 2, 0.1분 만에 종료. 코드 argparse가 --aux-labels·--split·--split-sha256(또는 LAB_* 환경 변수)을 요구하나 러너는 해당 환경 변수를 설정하지 않아 학습 전에 실패. 실험 결과 아님.
조치: command에 Drive 경로 지정 — 005 aux_labels.json(`$DCC_RUN_ROOT/lab/M3-ROBERTA-005/`), P0 split.json(`$DCC_RUN_ROOT/lab/M3-KCBERT-002/`, sha256 3568163751bc…1f9, 기존 metrics의 split_sha256). 코드·커밋은 그대로.
위험: 두 파일의 Drive 실재와 KCBERT-002 split 형식이 코드의 rows_sha256 검사와 맞는지는 이곳에서 확인 못 함. 같은 실험 재시도 1회 소진, 또 실패하면 코드 PR 수정 필요.
