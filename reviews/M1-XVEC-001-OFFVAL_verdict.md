VERDICT: 채택
- 공식 Validation 3,640건(여성 1,959 / 남성 1,681) 전부 평가. 고정 결합 LR(52D+x-vector) 정확도 0.9747 vs 기존 52D LR 0.9511: +2.36%p. 성공 기준(+0.5%p, 0.9561 이상) 충족.
- Training holdout 0.9738과 공식 Val 0.9747이 거의 같아 holdout 이득이 공식 Val에서도 재현된다. 이번이 최초 공식 Val 평가이며 재학습·모델 선택·threshold 튜닝 없음(`fitting_performed=false`).
- 성별 recall: F 0.9796, M 0.9691. 혼동행렬 F→M 오류 40건, M→F 오류 52건으로 한쪽 쏠림 없음.
- identity 기록: 가중치 SHA256 4fffb8aa…, WavLM 고정 revision 1bfd64ec…, 인코더·입력 SHA256, rows 3640 확인. 규정 위반 없음(공식 Val은 평가에만 사용, 입력은 음성+startAt/endAt/Speaker, 외부 API 없음). 소요 23.2분(T4).
- 후속: M1 제출 후보를 이 결합 LR(M1-XVEC-001)로 갱신. 공식 Val 사용 1회 소진(미션당 예산 6). 제출 추론 시 x-vector 모델 로컬 경로와 추론 시간 확인 필요.
