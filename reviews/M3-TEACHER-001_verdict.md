VERDICT: 재시도
- 실패 원인은 실험 설계가 아닌 환경: `get_peft_model`에서 ImportError (Colab torchao 0.10.0, peft는 0.16.0 이상 요구). 학습 전 1.6분 만에 종료, metrics 없음
- 모델 로드까지는 정상 통과(lm_head UNEXPECTED는 무시 가능한 경고)이므로 가설 검증은 아직 이루어지지 않음
- 조치: 명세 command 앞에 `pip uninstall -y torchao`를 추가(torchao 미사용). 그 외 설정·예산(A100, 5h)은 그대로
- 재시도 1회 사용. 다시 실패하면 중단하고 보고
