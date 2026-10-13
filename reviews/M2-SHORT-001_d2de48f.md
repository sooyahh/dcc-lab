# M2-SHORT-001 검토 (d2de48f)

1. Validation 누수: OK. Training zip과 내부 D/H만 사용.
2. 분할 누수: OK. call_id 분할은 SSL-003 파일을 그대로 쓴다. H는 학습과 best 선택에 쓰지 않는다.
3. 입력 필드: OK. 길이는 스텝을 고를 때만 쓰고 네트워크 입력은 파형 창이다.
4. M2 발화 독립성: OK. 다른 발화 파형은 SSL-004와 같은 학습 중 겹침 증강(다른 통화, 15%)에만 쓰인다. 추론 입력은 대상 발화뿐이다.
5. 외부 데이터·네트워크: OK. 부모 가중치는 lab/M2-SSL-004/best.ckpt.
9. requirements: OK. 변경 없음.
6. 실행 계약: OK. ckpt_last.pt 재개, 15분 저장, metrics.json. num_workers=0이라 에폭이 SSL-004보다 길 수 있다.
7. 명세 일치: OK. 70%·1.2초·에폭 1·학습률 1e-5/1e-4가 코드와 같다. 첫 에폭 트랜스포머 동결은 하지 않는다.
8. 명백한 버그: 없음.

MINOR: 데이터 로더 워커가 0이라 한 에폭이 길어진다. budget 6시간 안에 두었다.

VERDICT: PASS
