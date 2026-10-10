VERDICT: 보류
- 2차 실패(0.2분, metrics 없음): torchaudio shim으로 speechbrain import는 통과했으나 `EncoderClassifier.from_hparams`가 Drive 모델 폴더에 심볼릭 링크를 만들지 못함(`OSError: [Errno 95]`, label_encoder.txt -> .ckpt).
- 실험 결과가 아닌 환경 호환성 문제이며 가설은 아직 판정 불가. GPU 시간 손실은 거의 없음.
- 같은 실험 재시도 1회를 이미 사용했고, 명세 수정만으로는 해결 불가(코드의 모델 로드 경로 수정 필요) → 재시도 대신 보류.
- 조치: 팀 PR #132에 `lab-fix` 라벨과 수정 지시(모델을 LAB_WORK 로컬로 복사해 로드, shim을 스크립트 내부로). Codex 수정 → 재검토 PASS 후 새 commit으로 재제출.
