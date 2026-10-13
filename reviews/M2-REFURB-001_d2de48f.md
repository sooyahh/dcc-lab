# M2-REFURB-001 검토 (d2de48f)

1. Validation 누수: OK. 공식 Validation 경로 없음.
2. 분할 누수: OK. SSL-003 call_id 분할. H는 최종 평가만.
3. 입력 필드: OK. 텍스트로 라벨을 고치지 않는다. JSON speaker는 그대로 두고, 손실 목표만 그 발화의 모델 확률과 섞는다.
4. M2 발화 독립성: OK. 부드러운 정답은 같은 발화의 로짓이다. 다른 발화 정보는 SSL-004와 같은 학습 증강에만 있다.
5. 외부 데이터·네트워크: OK.
9. requirements: OK. 변경 없음.
6. 실행 계약: OK. 재개·metrics.json.
7. 명세 일치: OK. 확신은 max(p, 1-p) ≥ 0.95, 혼합 0.9/0.1, SupCon은 제공 라벨. 겹침 accuracy가 내려가면 adopted=false.
8. 명백한 버그: 없음.

MINOR: 확신 있는 오답이 겹침 발화이면 그 구간 학습이 약해질 수 있다. 그 경우 채택 조건 (3)이 막는다.

VERDICT: PASS
