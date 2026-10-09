변경 파일: `scripts/lab/m3-kcbert-012.py`

005 기반으로 fp32 BCE + soft macro-F1 손실, `>= 0.5` 판정, epoch별 손실 항·빈 예측 수 기록을 구현했습니다. import와 smoke 통과. torch 부재로 텐서 검증은 생략했으며 학습은 실행하지 않았습니다.

COMMAND: python scripts/lab/m3-kcbert-012.py --out "$LAB_OUT"