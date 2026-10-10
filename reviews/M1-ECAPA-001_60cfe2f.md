# M1-ECAPA-001 검토 (PR #132, 60cfe2f)
이전 PASS(1a88417) 이후 변경: 모델을 LAB_WORK 로컬로 원자적 복사 후 로드(`stage_model`), `LocalStrategy.COPY`, torchaudio shim 내장. 전체 재검토.
1. Validation 누수: OK — Training TL_/TS_ zip만 사용(`base.prepare_rows`), `uses_official_val`=false, `official_val=None`
2. 분할 누수: OK — 성별 층화 8:2 seed 42, call_id 교집합 assert(:236 부근)
3. 입력 화이트리스트: OK — 신고자 구간 음성(startAt/endAt/Speaker)만, 성별은 정답으로만
4. M2 발화 독립성: 해당 없음
5. 외부 데이터·네트워크·비밀: OK — 고정 revision 40자 `snapshot_download`를 `$DCC_RUN_ROOT/models/`로(허용), 이후 LAB_WORK 로컬 복사본만 로드. Drive 쓰기는 모델 폴더 마커와 LAB_OUT뿐. 토큰 접근 없음
9. requirements.txt: OK — `speechbrain==1.0.3` 1줄만 추가
6. 실행 계약: OK — 2000통화 청크·헤드별 ckpt 원자적 저장으로 재개, metrics.json+best.ckpt 있으면 종료, holdout_probs.npy(a,b,c,d 열)·val_files.txt 저장
7. 명세 일치: OK — (a)(b)(c)(d)와 진단용 x-vector 단독, 같은 LR 헤드, McNemar·오답 겹침·길이 구간·시간 기록. 기준 특징 재사용은 config/split/duration/shape 검증 후에만
8. 명백한 버그: 없음 — 확률 열은 classes_.index(1)=M, seed 고정. 이전 실패(심볼릭 링크 Errno 95)는 speechbrain 1.0.3 `fetch`/`link_with_strategy` 확인 결과 COPY 전략 + source==savedir(동일 경로는 그대로 반환)로 해소됨. `from_hparams`의 `local_strategy` 인자도 1.0.3에 존재

[심각도: MINOR] scripts/lab/m1-ecapa-001.py:60-75 — 실제 speechbrain 모델 로드는 이 검토에서 실행하지 못함. 실패해도 데이터 작업 전 main 시작 직후라 GPU 손실은 작음
[심각도: MINOR] :21 CONFIG에 `baseline=base.CONFIG` 포함 — 팀 main의 m1-xvec-001 CONFIG 변경 시 재개가 mismatch로 실패(의도된 안전장치)

BLOCKER·MAJOR 0건.
VERDICT: PASS
