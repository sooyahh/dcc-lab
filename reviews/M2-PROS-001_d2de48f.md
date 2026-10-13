# M2-PROS-001 검토 (d2de48f)

1. Validation 누수: OK. Training zip과 내부 D/H만 사용. 저장된 H 확률은 평가 조합에만 쓴다.
2. 분할 누수: OK. SSL-003 call_id 분할. best는 D accuracy.
3. 입력 필드: OK. F0·로그 에너지·비주기성은 대상 파형에서만 계산한다.
4. M2 발화 독립성: OK. 다른 발화를 섞지 않는다. 앙상블 평균은 이미 저장된 발화별 확률이다.
5. 외부 데이터·네트워크: OK. WavLM 가중치를 다시 받지 않는다.
9. requirements: OK. 변경 없음.
6. 실행 계약: OK. 에폭 끝과 15분마다 ckpt_last.pt, metrics.json.
7. 명세 일치: OK. 6에폭, 통화당 4발화, 4멤버 가중치 1/4 고정. 확률 파일이 없으면 채택하지 않는다.
8. 명백한 버그: 없음. CNN 열 이름이 cnn으로 시작할 때 평균한다.

MINOR: 3멤버 확률이 없으면 주 지표는 운율 모델 단독 accuracy가 되고 adopted는 false다.

VERDICT: PASS
