# M1-XVEC-001-OFFVAL 검토 (1d728f2)

- Validation 사용을 명시한 고정 후보 평가이며 학습·튜닝 API 호출이 없다.
- 특징 입력은 신고자 음성과 Speaker/startAt/endAt만 사용한다. gender는 전체 특징 추출 후 점수 계산에만 읽는다.
- 기존 564D head, 고정 revision의 WavLM을 local_files_only로 로드한다. seed 42의 기존 학습 head를 변경하지 않는다.
- Validation WAV/JSON 3640쌍, stem 중복, 특징 크기 및 유한값을 검사한다. 전체 input/head/encoder hash가 맞을 때만 캐시를 재사용한다.
- metrics.json 계약 충족, CSV와 metrics는 원자적 교체. LAB_WORK/LAB_OUT 외 데이터 쓰기 없음. 압축 해제 경로 탈출 방지는 기존 helper가 검사한다.
- torch.inference_mode 및 eval 사용. 전용 sklearn1.6.1 경로로 head 직렬화 버전을 맞춘다. requirements 변경 없음.
- 공식 평가 예산 미소진 확인, 중복 작업 없음. 현재 running 작업 이동/중단 없음.
- py_compile 및 git diff --check 통과. 로컬 전체 평가 병행 중; 공식 점수 아직 없음. GPU에서 같은 고정 모델의 실행을 검증한다.

VERDICT: PASS
