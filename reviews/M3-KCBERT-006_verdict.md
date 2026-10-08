VERDICT: 기각
- 3-seed(42/43/44) 평균 Macro F1 0.5883 vs KCBERT-005 0.6092: -0.0209. 성공 기준(+0.01 이상, 최소 2개 seed 0.6092 초과) 미충족. seed별 0.5829 / 0.5971 / 0.5848로 3개 모두 0.6092 미만.
- 동일 분할(Train 23,408 / Val 5,792), threshold 0.5, 최종 epoch(5) 평가, 공식 Val 미사용.
- Micro F1 0.6145(005: 0.6344). 오심 F1 평균 0.238(005: 0.283), 두통 0.448(005: 0.488)로 희소 증상 수렴 가설과 반대로 오히려 하락 — epoch 확대에 따른 과적합 가능성.
- 주의: 결과 notes에 "KCBERT-005 unavailable: reused 003, exact baseline parity unverified" 기록. 다만 하락폭이 seed 편차(~0.007)보다 크고 003(0.5990)에도 못 미쳐 판정은 유지.
- 후속: epoch 증가·가중 미세 조정은 재제안하지 않음. KCBERT-005(3 epochs)를 우선 후보로 유지.
