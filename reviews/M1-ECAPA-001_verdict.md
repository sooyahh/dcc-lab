VERDICT: 재시도
- 1회차 실패 원인은 실험 결과가 아닌 환경 호환성: Colab의 torchaudio에 `list_audio_backends`가 없어 speechbrain 1.0.3 import 단계(prepare_model, main 직후)에서 종료. 0.2분, 데이터·학습 단계 미도달, metrics 없음.
- 검토(PASS, 1a88417)에서 MINOR로 예고한 "speechbrain 로컬 로드 미검증" 범주의 문제이며 GPU 시간 손실은 거의 없음.
- 조치: commit(1a88417)·코드는 유지하고 명세 command에서 `torchaudio.list_audio_backends`만 shim한 뒤 원 스크립트를 runpy로 실행. 같은 실험 재시도 1회 사용.
- 이 shim으로도 speechbrain 다른 import 호환 문제가 나오면 코드 PR(#132) 수정이 필요하며, 그 경우 사용자 보고.
- 가설(ECAPA 추가 효과)은 아직 판정 불가.
