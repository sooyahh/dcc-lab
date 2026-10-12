VERDICT: 보류
- failed/00_M2-SSL-003.json (colab-a, A100, 11.5분): 학습 첫 배치에서 `AttributeError: module 'torchaudio' has no attribute 'info'` (`scripts/lab/m2-ssl-003.py:181`). metrics.json 없음.
- 실험 결과가 아니라 코드/환경 결함이라 가설 판정 불가. WavLM 다운로드·로드는 정상(Fetching 5 files, Loading weights 248/248).
- 명세 변경 불필요(재시도 횟수 attempts 1/3, 재시도 1회 소진 아님). 이전 검토(9340ec6)가 놓친 결함이라 52ee761 재검토를 FAIL로 기록(`reviews/M2-SSL-003_52ee761.md`).
- 조치: PR #191에 lab-fix + 수정 지시(`dcc_data.audio.read_wav_info/read_wav_frames`로 구간 읽기, load_segment 스모크 검사). 수정 후 재검토 PASS 시 재제출.
