VERDICT: 채택
- Training 8:2 holdout(seed 42, 5,840통화)에서 결합 LR(52D+x-vector) 정확도 0.9738 vs 52D 단독 0.9502: +2.36%p. 성공 기준(+1.0%p 이상) 충족.
- 같은 분할 paired McNemar 정확검정 p=3.5e-20 (52D 오답→결합 정답 187건, 반대 49건). 단일 seed지만 홀드아웃 5,840건에서 개선이 seed 편차보다 훨씬 크다. x-vector 단독도 0.9707로 개선의 대부분이 x-vector에서 나온다.
- 성별 recall: F 0.9775(52D 0.9582), M 0.9696(0.9411). 두 성별 모두 개선, 한쪽 쏠림 없음.
- 공식 Val 미사용(`official_val` null), Training 서울 데이터만, 입력은 음성+startAt/endAt/Speaker, 외부 API 없음(공개 WavLM 가중치 로컬 사용). 규정 위반 없음. 소요 73.6분, 추출 3.05통화/초.
- 후속: 코드 PR #112에 `lab-adopted`. 제출 후보 판단은 공식 Val 예산(미션당 6) 안에서 별도 진행. 제출 추론 시 x-vector 모델 로컬 경로 사용 및 추론 시간 확인 필요.
