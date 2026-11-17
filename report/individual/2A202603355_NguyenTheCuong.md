# Báo cáo cá nhân Lab09 — Evaluation and Failure Analysis

## 1. Thông tin

- Họ tên: Nguyễn Thế Cường
- MSSV: 2A202603355
- Lớp: L3A
- Email: 26ai.cuongnt2@vinuni.edu.vn
- GitHub: Chill2004
- Ngày thực hiện: 17/11/2026
- Repo thực hiện: https://github.com/Chill2004/K5-L3A-DAY08-NguyenTheCuong-2A202603355-FromWorkflowsToAgents
- Nhánh làm bài: starter/d09
- Commit code/grader đã kiểm chứng: [f3e3a70d96018666c7fc2f483e901d67984307dd](https://github.com/Chill2004/K5-L3A-DAY08-NguyenTheCuong-2A202603355-FromWorkflowsToAgents/commit/f3e3a70d96018666c7fc2f483e901d67984307dd).
- URL PR: bổ sung sau khi mở PR.

## 2. Mục tiêu và phạm vi

Thực hiện Lab09 trên bản fork cá nhân của repo Lab08, copy overlay gồm src/, docs/ và .github/. Giữ code trong src/lab8/ theo yêu cầu khóa agent. Dùng swarm tham chiếu làm baseline để xây hệ thống đánh giá, phân tích lỗi và gate chặn regression.

Phần thực hiện gồm Core M0–M4, Advanced M5–M6 và Expert M7. Các số liệu dưới đây lấy từ lần chạy thực tế, JSON sinh bởi công cụ và output kiểm thử. Bonus port sang Inspect AI/DeepEval chưa thực hiện.

## 3. Các phần đã thực hiện

### M0 — Môi trường

Tạo môi trường Python 3.12, cài requirements của Lab08 và Lab09. Smoke đạt M0 PASS. Eval set v1 gồm 14 item, nhãn tách riêng khỏi input. Làm bài trên nhánh starter/d09 của repo cá nhân.

### M1 — Taxonomy và trace case

Điền docs/failure_taxonomy.md với mã FM theo starter, định nghĩa, layer, bằng chứng trace và phương pháp grader. Có tám FM quan sát lỗi dương tính và FM-09 có đối chứng chặn truy cập khác principal. Không coi case đối chứng là bằng chứng lỗi đã phát sinh.

Phân tích seeded_regression C-002@11 trong docs/trace_case.md. Event 2 đọc order.delay_days=2, event 3 model_override thay thành 5 từ ticket. Sau đó quote và ledger là 20000 VND thay vì 0. Bản fixed giữ dữ kiện order, trả denied và không refund. Thêm regression test để xác nhận sự khác biệt.

Bổ sung ánh xạ failure_modes theo claim và provenance trong evalset.py. v1 có SHA ec9e461eceaa. Nhãn nằm trong labels_v1.json. Các tag/layer được phân tích có AI hỗ trợ, chưa được đối chiếu key anchor riêng của giảng viên.

### M2 — Judge calibration

Hoàn thành confusion matrix với FAIL là lớp positive, precision/recall, Cohen kappa và Rogan–Gladen trong stats.py. Đọc nhãn, câu trả lời và note từ CSV, viết audit 10 bất đồng trong docs/judge_audit.md, có đề xuất sửa rubric.

| Judge | TP | FP | FN | TN | Precision | Recall | Kappa | Kết luận |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Tone | 24 | 4 | 6 | 66 | 0.857 | 0.800 | 0.757 | Đạt cả ba sàn |
| Helpful | 9 | 0 | 21 | 70 | 1.000 | 0.300 | 0.375 | Loại khỏi gate |

Helpful bỏ sót 21/30 lỗi dù precision cao. Tỉ lệ lỗi quan sát Tone 0.28, Helpful 0.09, đều được hiệu chỉnh về 0.30. Rogan–Gladen hiệu chỉnh tỉ lệ tổng thể, không sửa verdict từng câu. Số ledger trong audit Helpful dẫn từ note của CSV, chưa xác minh độc lập bằng SQLite.

### M3 — Trajectory assertion

Triển khai ApprovalBypass để kiểm refund khi approval không hợp lệ hoặc có unexpected ledger rows, RefundAmountCorrect để so tiền thực ghi với nhãn. Bổ sung ReplyAmountCorrect bắt FM-08 và ProposalCorrect so entitlement đầy đủ trước khi host cap hoặc trừ lịch sử.

ProposalCorrect giải quyết khoảng thiếu quan sát được ở năm trial C-013 bị trừ proposal về 0. Trước khi bổ sung, detection là 15/20. Sau khi thêm, lệnh mutation --detect đạt 20/20=100%, false alarms trên fixed là 0/70=0%. Không đưa TrialPass vào bộ phát hiện để tránh tự dùng nhãn làm dự đoán.

ReplyAmountCorrect có giới hạn đặc biệt đối với swarm cũ thiếu event reply. Trường hợp này trả True theo quy ước không áp dụng, không chứng minh nội dung reply đúng. Các variant thiếu reply bị đánh fail. Regex hỗ trợ số nguyên VND và có thể báo nhầm câu nhắc nhiều khoản tiền với ý nghĩa khác nhau. Giới hạn được ghi trong eval card.

### M4 — Paired bootstrap và CI gate

Triển khai paired bootstrap trên cùng item, dùng per-item mean qua seed, 1000 resample, percentile, RNG 2027, CI 95%. Bổ sung sections.eval trong harness_map.yaml, tăng harness_map_version lên 1.2.

| So sánh v1 | Delta pass_rate | CI 95% | Gate |
|---|---:|---|---|
| Swarm baseline với chính nó | 0.000 | [0.000, 0.000] | exit 0 |
| Fixed với baseline | +0.014 | [0.000, +0.043] | exit 0 |
| Seeded regression với baseline | -0.271 | [-0.500, -0.057] | exit 1 |

Regression bị chặn ở pass_rate, refund_amount_correct, reply_amount_correct và proposal_correct. CI pass_rate khớp tham chiếu của đề. Metric có CI chạm 0 vẫn có thể bị chặn bởi sàn tuyệt đối, không diễn giải mọi BLOCK là giảm có ý nghĩa thống kê.

### M5 — Eval set v2 và slice

Điền fm_map.yaml cho tám cơ chế trong adversarial pack, xây v2 gồm 28 item, SHA feef2ca73e4f. Mọi FM bị tấn công có ít nhất ba item, checker sạch. Các item public có tag bổ sung làm đối chứng cho clause và sibling, nên đã sinh lại report v1 với SHA mới.

Triển khai slice_check. money_movement và adversarial dùng min pass_rate 0.95, no_significant_drop và blocking. Denial giữ min 0.90. Slice regression có pass_rate chung 0.9357, vẫn trên sàn toàn cục 0.85 nhưng bị chặn qua slice và proposal_correct.

### M6 — Độ ổn định và A/A

Hoàn thành pass_at_k và pass_hat_k, kiểm đầu vào và công thức lấy mẫu không hoàn lại. pass_hat_5 min 0.80, blocking. Baseline v2 pass_hat_5=0.8929.

A/A trên hai bộ seed 11/22/33/44/55 và 66/77/88/99/110 cho delta bằng 0 trên mọi metric. Model thật cần đo dải nhiễu qua nhiều lần chạy để chọn dung sai. Năm seed chưa bảo đảm phát hiện lỗi hiếm. Với xác suất lỗi độc lập 1/3, xác suất không gặp lỗi trong năm lần là khoảng 13.2%, đây là minh họa xác suất chứ không phải phép đo trên MockLLM.

### M7 — Integrity, ratchet và mutation

Triển khai kiểm tra số dòng, item/seed, dòng trùng, NaN/inf, evaluator_failures, row thiếu metric, aggregate không khớp row và slice tag bị sửa. Ratchet chặn bỏ metric/slice, bỏ blocking/CI hoặc nới threshold trên cùng eval-set version khi có base-spec.

| Variant | Kết quả |
|---|---|
| fixed | merge |
| honest_refactor | merge |
| seeded_regression | block |
| slice_regression | block |
| flaky_regression | block |

Mutation score 3/3, false alarms 0. Bốn trap evaluator_errors_as_nan, dropped_failing_rows, cherry_picked_seeds và loosened_spec đều bị chặn. Gate riêng từng trap trả exit 1 với lý do INTEGRITY. Baseline v2 so với chính nó merge.

## 4. Bằng chứng và tài liệu bàn giao

| File | Nội dung |
|---|---|
| [failure_taxonomy.md](../../docs/failure_taxonomy.md) | Phân loại FM và bằng chứng |
| [trace_case.md](../../docs/trace_case.md) | Case C-002 và regression test |
| [judge_audit.md](../../docs/judge_audit.md) | Calibration và 10 bất đồng |
| [eval_card.md](../../docs/eval_card.md) | Kết quả v1/v2, ngưỡng, lệnh tái lập và giới hạn |
| [PRD_v1.1.md](../../docs/PRD_v1.1.md) | Tiêu chí nghiệm thu, gate và trách nhiệm |
| src/harness_map.yaml | sections.eval, version 1.2 |
| src/reports/local_validation.txt | Output kiểm tra cuối do lệnh chạy sinh |

| Report | Run id |
|---|---|
| baseline_v1.json | E-swarm-20261117-ec9e |
| eval_fixed.json | E-fixed-20261117-ec9e |
| eval_seeded_regression.json | E-seeded_regression-20261117-ec9e |
| baseline_v2.json | E-swarm-20261117-feef |
| eval_slice_regression.json | E-slice_regression-20261117-feef |

Toàn bộ test của repo đạt 361 passed. Smoke M0 PASS, eval set v1/v2 0 problem(s), ci_check baseline/spec exit 0. Dữ liệu JSON được sinh bằng script. GitHub Actions chưa được xác nhận vì chưa đến bước push và mở PR.

## 5. Khó khăn và xử lý

- Pytest gặp WinError 5 ở thư mục tạm mặc định. Chuyển PYTEST_DEBUG_TEMPROOT vào .pytest_cache/temp trong repo và chạy lại.
- Metric spec có dòng no_significant_drop thừa gây ParserError. Xóa dòng thừa, kiểm YAML rồi sinh lại report.
- Class ReplyAmountCorrect được tham chiếu trước khi định nghĩa gây NameError. Đặt class trước registry GRADERS và chạy test.
- Test trace đăng ký variant trong registry toàn cục làm hai test host thất bại. Bổ sung fixture phục hồi registry sau test, toàn bộ bộ test đã xanh.
- Swarm cũ thiếu event reply khiến metric ban đầu fail tất cả trial. Bổ sung quy ước không áp dụng có giới hạn và công khai trong báo cáo.
- Khi sinh tài liệu bằng script có lỗi mã hóa tiếng Việt. Ghi lại tài liệu UTF-8 và kiểm tra hiển thị trước bàn giao.

## 6. Công cụ AI và cách kiểm chứng

Dùng ChatGPT/Codex để giải thích bài, gợi ý và hỗ trợ viết stats/grader/gate, đọc trace, viết test và tổng hợp tài liệu. Code và báo cáo có hỗ trợ của AI. Bản thân đã chạy lại các lệnh được hướng dẫn trong terminal và đối chiếu output từng mốc, gồm test 361 passed, calibration, detection, gate, mutation, A/A và traps.

Các kết luận audit dựa trên nhãn và note replay. Các lựa chọn mapping, layer, sàn mới của v2 và quy ước reply absent cần người học review trước khi nộp. Không tự tạo số liệu hoặc hash commit chưa có. Báo cáo này mô tả bằng chứng đã làm, không tự khẳng định mức độ thành thạo chưa được kiểm tra.

## 7. Mức độ hoàn thành và việc còn lại

Các mốc Core, Advanced và Expert đã có triển khai và kiểm thử công khai cục bộ. Code đã được commit và push lên starter/d09. Cần mở PR đúng repo và xác nhận hai job eval-gate/eval-gate-v2 xanh theo bước nộp. Mô tả PR cần output regression block, mutation 3/3, A/A và bốn trap.

Bộ chấm ẩn và key anchor do giảng viên giữ chưa được kiểm tra. MockLLM, bộ public nhỏ và judge replay chưa chứng minh chất lượng trên người dùng/model thật. Bonus port Inspect AI/DeepEval là tùy chọn, chưa thực hiện.

Nội dung cần tự luyện thêm theo các vấn đề đã gặp là đọc traceback, kiểm thứ tự khai báo class, YAML, quản lý phạm vi dữ liệu đánh giá và giải thích các chỉ số trước khi dùng gate. Người học cần tự xác nhận mức độ hiểu và bổ sung nhận xét cá nhân nếu muốn, phần này không thay thế đánh giá trực tiếp của giảng viên.

## 8. Output và bằng chứng có thể đối chiếu

Các file log trong thư mục evidence được tạo từ stdout/stderr của lệnh chạy thực tế. Mỗi log ghi lệnh và exit code. Đây là bản văn bản có thể đọc trực tiếp khi review báo cáo.

| Nội dung cần đối chiếu | File bằng chứng |
|---|---|
| Toàn bộ test 361 passed, checker v1/v2, kiểm baseline/spec và bốn trap trả exit 1 với INTEGRITY | [local_validation.txt](evidence/local_validation.txt) |
| Calibration Tone PASS, Helpful FAIL và 10 bất đồng | [judge_calibration.txt](evidence/judge_calibration.txt) |
| Baseline/fixed merge và seeded regression block, kèm CI | [core_gates.txt](evidence/core_gates.txt) |
| Detection 100%, false alarms 0% | [detection.txt](evidence/detection.txt) |
| Scorecard đủ năm variant, mutation 3/3, false alarms 0 | [mutation.txt](evidence/mutation.txt) |
| Hai bộ seed A/A và delta từng metric | [aa.txt](evidence/aa.txt) |

### Report JSON do công cụ sinh

- [Baseline v1](../../src/reports/baseline_v1.json), run E-swarm-20261117-ec9e.
- [Fixed v1](../../src/reports/eval_fixed.json), run E-fixed-20261117-ec9e.
- [Seeded regression v1](../../src/reports/eval_seeded_regression.json), run E-seeded_regression-20261117-ec9e.
- [Baseline v2](../../src/reports/baseline_v2.json), run E-swarm-20261117-feef.
- [Slice regression v2](../../src/reports/eval_slice_regression.json), run E-slice_regression-20261117-feef.

Các report cần có trong commit nộp để link hoạt động trên GitHub. Không chỉnh tay JSON. Trace và SQLite dùng phân tích cục bộ, không đưa vào thư mục evidence. Hash code đã kiểm chứng được ghi ở mục 1. URL PR sẽ bổ sung sau khi mở PR.
