# M3-DEBERTA-001 검토 (c080f17, 수정 후 재검토)

이전 검토(66908f1, PASS) 이후 변경은 토크나이저 로딩 수정뿐이다 (`git diff 66908f1 c080f17`). 나머지 항목은 이전 검토 결과 유지.

1. Validation 누수: OK — 변경 없음, 공식 Val 경로 없음
2. 분할 누수: OK — 변경 없음
3. 입력 화이트리스트: OK — 변경 없음 (probe는 고정 문자열만 사용)
4. M2 독립성: 해당 없음
5. 외부 데이터·네트워크·비밀: OK — 토크나이저는 `local_files_only`/로컬 `tokenizer.json`만 읽음. 고정 revision(016360a) 저장소에 `tokenizer.json`·`tokenizer_config.json`·`special_tokens_map.json`이 있음을 확인(allow_patterns `tokenizer*`가 포함)
9. requirements.txt: OK — 변경 없음
6. 실행 계약: OK — 변경 없음. 토크나이저 로딩·probe는 `prepare_model()`에서 데이터 준비 전에 수행되어 실패 시 즉시 종료
7. 명세 일치: OK — max_length 256, 앞부분 절단(truncation_side=right), 모델 토크나이저 사용
8. 버그: 없음 — `AutoTokenizer`가 `TypeError`(보고된 Unigram dict 오류)를 내면 `PreTrainedTokenizerFast(tokenizer_file=…)`로 폴백하고, probe(CLS/SEP 프레임, 패딩 ID, 한글이 특수토큰만으로 변환되지 않는지)로 검증한다. smoke가 해당 경로를 모의 테스트함

- [MINOR] load_tokenizer — 폴백 토크나이저는 실제 Colab 환경에서 아직 실행된 적 없음. 실패해도 학습 전(수 초)에 종료되므로 GPU 시간 손실 없음
- [MINOR] (이전 지적 유지) ECE가 전 라벨 pooled 15구간 — 판정 시 정의 참고

VERDICT: PASS
