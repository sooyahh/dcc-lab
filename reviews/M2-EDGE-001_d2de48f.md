# M2-EDGE-001 검토 (d2de48f)

1. Validation 누수: OK. Training zip과 내부 H만 읽고 uses_official_val=false.
2. 분할 누수: OK. SSL-003 split.json을 해시 확인 후 사용. 학습이 없어 분할을 다시 맞추지 않는다.
3. 입력 필드: OK. 파형과 startAt/endAt. 텍스트 키를 읽지 않는다.
4. M2 발화 독립성: OK. 네 시점은 대상 구간 안에서만 자른다. 통화 단위 정규화·다른 발화 없음.
5. 외부 데이터·네트워크: OK. SSL-004 로컬 체크포인트와 기존 wavlm-large 경로. H 확률 파일은 읽기 전용.
9. requirements: OK. 변경 없음.
6. 실행 계약: OK. 256행마다 edge_progress.npz를 원자적으로 남기고, metrics.json이 있으면 건너뛴다.
7. 명세 일치: OK. 확률 산술평균, threshold 0.5, 채택 조건이 코드의 adopted와 같다.
8. 명백한 버그: 없음. 너무 짧은 발화는 전체 구간으로 되돌리고 건수를 기록한다.

MINOR: 저장된 SSL-004 확률과의 차이는 fp16 재로드 때문에 1e-3을 넘을 수 있다. 채택 비교는 같은 실행의 전체 구간으로 한다.

VERDICT: PASS
