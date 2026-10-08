# M2 L2 CNN 3-seed 재학습 요청

M2 L2 CNN(SpeakerCNNLarge) 3-seed 재학습을 맡아 줄 수 있을까? Training 스펙트로그램은 미리 만들어 두었으니 Colab에서 노트북만 돌리면 돼.

## 준비물
- Colab Pro (T4 GPU 기준 3 seed 전부 약 37시간, 컴퓨팅 단위 약 70 소모. 단위가 부족하면 끝난 seed까지만으로도 제출 가능)
- 노트북: 팀 저장소 `main`의 `notebooks/mission2_l2_retrain.ipynb`

## 1. Drive 바로가기 (공유 메일 받은 뒤)
공유받은 항목을 Drive 웹에서 우클릭 → **정리 → 바로가기 추가 → 내 드라이브(최상단)**. **이름은 바꾸지 말 것.**

| 항목 | 권한 | 용도 |
|---|---|---|
| `dcc_runs` 폴더 | 편집자 | 미리 만든 스펙트로그램(`dcc_runs/m2_l2_spec/`) 읽기 + 체크포인트 저장(`dcc_runs/m2_l2_rerun_6cc1181/`) |
| `dcc2026-prelim-main-6cc1181.zip` | 뷰어 | 학습 코드 (노트북 0번 셀이 sha256 검사) |
| `대학부 데이터` | 주최 측 공유 링크 | 공식 데이터 (이미 있으면 생략) |

자세한 절차는 저장소의 `docs/team_colab_setup.md` 참고.

## 2. 노트북에 한 줄 채우기
설정 셀의 아래 줄을 그대로 바꿔 넣기 (값은 Training 스펙트로그램 sha256):
```python
TRAIN_PACKED_SHA256 = {"m2_spectrograms_packed.npy": "69a770c8100f6851c2f6a642a801dc1e0dd0a14691bc3b37f047ebf2ba4712b8", "m2_spectrogram_index_packed.parquet": "6afe3caacbf5916e291009849d4ff27d32ead3699b80c1a23ec038c4eda79aad"}
```
나머지 설정(`SEEDS`, `EPOCHS=30`, `RUN_BUILD=False` 등)은 건드리지 말 것.

## 3. 실행
1. 런타임 → 런타임 유형 변경 → **T4 GPU**
2. **모두 실행**
3. 끊기면 그냥 다시 **모두 실행**. 에폭 단위로 이어서 학습함 (ckpt가 에폭마다 Drive에 저장됨)
4. 3 seed를 다 못 돌리면 `SEEDS_DONE`에 끝난 seed만 남기고 마지막 셀(앙상블·평가)만 실행

## 4. 주의
- **같은 노트북을 두 사람이 동시에 돌리면 안 됨** (같은 체크포인트 폴더를 써서 충돌). 시작할 때 단톡에 "M2 L2 시작" 한 줄 남겨 줘
- 노트북 코드와 출력 폴더 이름은 수정하지 말 것 (재현성 검사가 걸려 있음)
- 공식 Validation은 평가만 함 (학습·에폭 선택에는 안 씀). 노트북이 이미 그렇게 되어 있음

## 5. 끝나면 알려 줄 것
- 마지막 평가 셀 출력 (공식 Val 정확도). **채택 기준: 87.26% 이상 + 끝난 seed 전부의 에폭 로그 완비**
- 출력 폴더: `dcc_runs/m2_l2_rerun_6cc1181/`
