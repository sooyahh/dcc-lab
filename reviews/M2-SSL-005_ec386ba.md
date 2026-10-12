# M2-SSL-005 검토 (sooyah/lab-m2-ssl-005, ec386ba) — 사령탑(로컬 세션)

M2-SSL-004 스크립트(cb0980a) 대비 diff를 직접 확인했다.
1. Validation 누수: OK — Training zip만, 공식 Val 경로 없음(SSL-004와 동일).
2. 분할: OK — M2-SSL-003 split.json 재사용·sha 확인, 없으면 실패.
3. 입력 화이트리스트·M2 발화 독립성: OK — 대상 발화 구간 파형만, 창 단위 normalize, 겹침 증강은 다른 통화·반대 라벨, SupCon은 라벨 기준(SSL-004와 동일 코드).
4. 백본: kresnik/wav2vec2-large-xlsr-korean 고정 revision 629c9a3, allow_patterns로 config·preprocessor·safetensors만 다운로드, 이후 local_files_only. Wav2Vec2Model(CTC 헤드 없음). config(revision 고정본): hidden 1024, 24층(hidden_states 25), layerdrop 0.1 → 코드에서 config.layerdrop=0.0(인코더가 forward 때 config를 읽으므로 유효), mask_time_prob 0.075·mask_feature_prob 0 명시, freeze_feature_encoder().
5. 진단: SSL-003/004 H_rows 키 집합 일치 확인 후 재정렬, 1:1 고정 평균 조합만(가중치 탐색 없음).
6. 실행 계약·metrics: SSL-004와 동일 코드 경로. best.ckpt metadata에 architecture·mask 값·preprocessor do_normalize 기록.
7. `PYTHONPATH=src python scripts/lab/m2-ssl-005.py --smoke` 로컬 통과(audio preflight, split hash·행 정렬, 슬라이딩 창, 샘플러, 원자적 저장, zip 해제).
8. requirements 변경 없음.

VERDICT: PASS
