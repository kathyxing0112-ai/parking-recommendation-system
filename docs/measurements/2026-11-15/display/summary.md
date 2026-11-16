# SR-13 display timing, 2026-11-15

Browser: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Claude/5.11492.5 Chrome/156.0.8078.75 Safari/537.36
Page: web_app at commit e89e9e1, Plan Your Trip popup open, browser pane visible (frame interval 16.7 ms).
Interval: search(trip) called until the frame with both recommendation cards was painted (display_ms).

| Series | Timing | n | mean ms | median ms | p95 ms | min ms | max ms | SD ms |
|---|---|---|---|---|---|---|---|---|
| spaced-2s | fetch_ms | 50 | 53.1 | 50.5 | 91.1 | 26.7 | 139.1 | 19.1 |
| spaced-2s | dom_ms | 50 | 55.3 | 52.4 | 93.6 | 29.2 | 140.2 | 19.0 |
| spaced-2s | display_ms | 50 | 68.3 | 65.2 | 98.9 | 32.4 | 149.1 | 16.9 |
| back-to-back | fetch_ms | 50 | 35.9 | 34.7 | 41.0 | 33.8 | 67.3 | 5.5 |
| back-to-back | dom_ms | 50 | 37.4 | 36.2 | 42.1 | 35.2 | 68.7 | 5.5 |
| back-to-back | display_ms | 50 | 66.6 | 66.6 | 66.8 | 50.1 | 83.5 | 3.4 |

spaced-2s: two cards shown in every run: True; results view and page visible in every run: True.

back-to-back: two cards shown in every run: True; results view and page visible in every run: True.
