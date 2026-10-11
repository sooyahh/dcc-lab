VERDICT: 보류
- 1차 실행이 학습 전, 토크나이저 로딩에서 실패했다(0.6분). `AutoTokenizer.from_pretrained`(deberta_v2 `Unigram(self._vocab, ...)`)가 `TypeError: 'dict' object is not an instance of 'Sequence'`를 냈다. Colab의 최신 transformers와 team-lucid/deberta-v3-xlarge-korean(revision 016360a) tokenizer 파일 형식이 맞지 않는 코드/환경 문제다.
- OOM·시간 초과가 아니라 명세 조정(배치·epoch)으로 풀리지 않는다. 같은 commit 66908f1을 재제출하면 똑같이 실패하므로 `재시도`로 보지 않고 재제출하지 않는다.
- 성능 결과는 없다(metrics.json 없음). 기준 ROBERTA-003 seed 42 0.6441, 성공 기준 0.6541 비교는 불가. 채택·기각 근거로 쓰지 않는다.
- 조치: 코드 PR #161에 `lab-fix` 라벨과 수정 지시(토크나이저를 모델 파일로 직접 로드하는 폴백, 예: slow `DebertaV2Tokenizer`/`sentencepiece`, 또는 `tokenizer.json`이 있으면 `PreTrainedTokenizerFast`, 모델 로드 전에 로컬 `tokenizer(...)` 시험 호출)를 남겼다. 고친 commit은 검토 후 재제출한다(실패 1회, 재시도 횟수 소진 아님). proposal 이슈 #39는 실험이 계속되므로 열어 둔다.
