# Development Environment

- Language / Version: Python 3.13
- Runtime: Local virtual environment
- Model Runner: Ollama
- Model: Qwen3 4B as the initial baseline (interprets chatbot messages into the six-field trip request; see the SPEC.md Model Response Contract)
- Forecasting model: LightGBM 4.7.0 quantile models below T_c and the lot/day/time-slot baseline after it (ALT-F2, ADR-0004), trained by `scripts/train_forecast.py`; model files in `estimate_arrival_time_availability/model/`
- Editor: Visual Studio Code, Pycharm(Katherine Xing)

## Coding Assistants

- Katherine Xing: Claude, codex
- Bochao Liang: Claude, codex
- Tingyu Huang: Claude, codex
- Linzi Gong: Claude, codex