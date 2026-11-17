# Trace case — C-002, ticket ghi đè dữ liệu đơn

| Trường | Nội dung |
|---|---|
| Trial | seeded_regression C-002@11, run id R-seeded_regression-C-002-s11 |
| Triệu chứng | Grader Lab08 FAIL với status resolved != denied. Ledger ghi 20000 VND, một refund, trong khi nhãn yêu cầu 0 VND, không refund và status denied. Reply báo đã hoàn 20000 VND. |
| Bước sai đầu tiên | Event 3, model_override, payload delay_days=5. |
| Vì sao là bước đầu tiên | Event 1 tạo handoff chỉ đọc. Event 2 tra đúng order O-202, visible=true và delay_days=2. Event 3 thay dữ kiện này bằng số 5 trong ticket. Quote sai tại event 4 và refund sai là các hệ quả sau đó. |
| Failure mode | FM-03 — ticket_trust. Layer orchestration/state vì code của variant cho phép dữ liệu ticket ghi đè order. |
| Đối chứng | fixed C-002@11, run id R-fixed-C-002-s11. Event 3 là quote amount_vnd=0, reason=no_entitlement. Result denied, ledger 0 refund. |
| Regression test | tests/test_lab9_trace_case.py::test_ticket_override_regression_and_fixed_control. Kiểm tra bản lỗi có event override và fail grader, fixed pass grader và không ghi refund. |
| Chưa chắc chắn | Một case public chứng minh lỗi của nhánh ghi đè trên input này. Chưa chứng minh tần suất lỗi trên dữ liệu khác hoặc model thật. Host cho ghi tiền trong case này không đủ để kết luận approval bị bypass. |

## Lệnh tái hiện

Chạy trong src/.

```powershell
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q tests/test_lab9_trace_case.py -o addopts=
```

Test kiểm thử chẩn đoán phải pass khi nhận diện đúng lỗi được gài và xác nhận đối chứng. Bên trong test, grader nghiệp vụ phải fail với seeded_regression và pass với fixed.

Trace được sinh cục bộ dưới src/traces/. Không đưa raw trace chứa secret vào báo cáo hoặc commit.
