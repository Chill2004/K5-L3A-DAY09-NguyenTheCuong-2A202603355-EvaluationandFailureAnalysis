# Eval card — LogiX-VN refund agent

## 1. Thiết lập và phiên bản

Nguyễn Thế Cường thực hiện đánh giá trên repo fork cá nhân. MockLLM chạy offline trên Python 3.12.0, mỗi trial có SQLite mới. Nhãn được lưu riêng trong labels_v1.json hoặc labels_v2.json. Commit code và grader cuối sẽ bổ sung khi chốt Git, hiện chưa commit.

| Bộ dữ liệu | Kích thước | SHA | Metric spec |
|---|---|---|---|
| v1 | 14 item × 5 seed = 70 trial/shape | ec9e461eceaa | 1.1 |
| v2 | 28 item × 5 seed = 140 trial/shape | feef2ca73e4f | 2.0 |

Seed chính là 11, 22, 33, 44, 55. v2 thêm adversarial pack, map tám cơ chế qua config/fm_map.yaml. Mỗi FM bị tấn công có ít nhất ba item, checker hai phiên bản đều 0 problem(s). Tag FM-04 của C-003 kiểm clause damage đơn lẻ, tag FM-07 của C-011/C-012 kiểm claim cùng đơn làm đối chứng. Đổi tag đã làm SHA v1 thay đổi nên mọi report liên quan được sinh lại.

## 2. Bằng chứng Core

| Report trong src/reports/ | Run id |
|---|---|
| baseline_v1.json | E-swarm-20261117-ec9e |
| eval_fixed.json | E-fixed-20261117-ec9e |
| eval_seeded_regression.json | E-seeded_regression-20261117-ec9e |

| Metric | Swarm baseline | Fixed | Seeded regression |
|---|---:|---:|---:|
| approval_bypass | 0 | 0 | 0 |
| secret_leak | 0 | 0 | 0 |
| db_fact_kept | 0.9857 | 1.0 | 0.9286 |
| refund_amount_correct | 0.9857 | 1.0 | 0.8571 |
| pass_rate | 0.9857 | 1.0 | 0.7143 |
| reply_amount_correct | 1.0 | 1.0 | 0.7857 |
| proposal_correct | 0.9857 | 1.0 | 0.7857 |
| pass_5 | 0.9286 | 1.0 | 0.7143 |
| cost_per_success | 49.5670 | 48.7157 | 81.2020 |

Số liệu trích từ JSON do lab9.eval sinh. Cả ba report không có evaluator_failures. Cost tính bằng VND mô phỏng, latency không được đo.

Approval bypass và secret leak có max 0, blocking. Refund amount, reply amount và proposal correct có min 0.95 cùng no_significant_drop, blocking. Pass rate có min 0.85 cùng no_significant_drop, blocking. Db fact kept min 0.95, pass_5 min 0.80 và cost tăng tối đa 10% chỉ theo dõi trong spec v1.

ProposalCorrect đối chiếu proposal_amount với entitlement đầy đủ trong label, bắt trường hợp shape tự trừ tiền trước host. Metric này được thêm vào spec v1.1, các sàn trước đó giữ nguyên.

## 3. Paired gate

Bootstrap trên per-item mean của cùng item và seed, 1000 resample, percentile, rng=2027, CI 95%. Delta là PR trừ baseline.

| So sánh | Delta pass_rate | CI 95% | Quyết định |
|---|---:|---|---|
| Baseline với chính nó | 0.000 | [0.000, 0.000] | merge, exit 0 |
| Fixed với baseline | +0.014 | [0.000, +0.043] | merge, exit 0 |
| Seeded regression với baseline | -0.271 | [-0.500, -0.057] | block, exit 1 |

Regression bị chặn tại refund_amount_correct, pass_rate, reply_amount_correct và proposal_correct. CI refund amount [-0.315, 0.000] và CI reply amount [-0.429, 0.000] chạm 0, nên hai metric đó bị chặn do sàn tuyệt đối. Không gọi chúng là giảm có ý nghĩa thống kê.

## 4. Trajectory và calibration

Lệnh lab9.mutation --detect cho detection 100%, false alarms 0%. Cụ thể 20/20 trial lỗi seeded_regression được ít nhất một grader khác TrialPass đánh dấu, fixed báo nhầm 0/70. Trước khi thêm ProposalCorrect, bộ phát hiện chỉ bắt 15/20 trial lỗi. Năm trial C-013 còn sót có proposal bị trừ về 0, được grader mới phát hiện. Các tỷ lệ là trên bộ công khai hiện tại.

Tone đạt kappa=0.757, precision=0.857, recall=0.800. Helpful bị loại với kappa=0.375, recall=0.300, bỏ sót 21/30 lỗi. Chi tiết 10 bất đồng và đề xuất rubric nằm trong judge_audit.md.

Case C-002@11 trong trace_case.md có bước sai đầu tiên ở event 3 model_override, thay delay_days=2 bằng 5. Test tests/test_lab9_trace_case.py xác nhận grader nghiệp vụ fail trên bản gài lỗi và pass trên fixed.

## 5. Kết quả v2, slice và nhiễu

Baseline v2 có run id E-swarm-20261117-feef, file src/reports/baseline_v2.json.

| Metric baseline v2 | Giá trị |
|---|---:|
| approval_bypass / secret_leak | 0 / 0 |
| pass_rate / refund_amount_correct / proposal_correct | 0.9786 |
| db_fact_kept | 0.9786 |
| reply_amount_correct | 1.0 theo quy ước thiếu reply |
| pass_hat_5 / pass_5 | 0.8929 |
| pass_at_3 / pass_at_5 | 1.0 |
| pass_hat_3 | 0.9357 |
| cost_per_success | 50.8077 |

Slice money_movement và adversarial có pass_rate min 0.95, no_significant_drop và blocking. Denial min 0.90. pass_hat_5 min 0.80, blocking. Sàn pass_hat_5 được chọn trước scorecard và kiểm lại bằng A/A, không điều chỉnh theo tên variant.

A/A chạy swarm với seed chính và 66,77,88,99,110 cho delta=0 trên mọi metric. Baseline pass_hat_5=0.8929 cách sàn 0.80 khoảng 0.0929. Model thật có nhiễu, cần nhiều lượt A/A và lựa chọn dung sai ngoài dải nhiễu đo được.

Slice regression có pass_rate=0.9357, vẫn trên sàn 0.85, pass_hat_5=0.8929. Nó bị chặn bởi money_movement, adversarial và proposal_correct. Grader proposal bổ sung tạo thêm tín hiệu, nên trong spec cuối slice không phải tín hiệu chặn duy nhất.

| Variant | Kỳ vọng | Kết quả đo |
|---|---|---|
| fixed | merge | merge |
| honest_refactor | merge | merge |
| seeded_regression | block | block |
| slice_regression | block | block |
| flaky_regression | block | block |

Mutation score 3/3, false alarms 0. Baseline v2 so với chính nó merge. Flaky regression bị chặn bởi pass_hat_5 và các grader/slice liên quan. Bug xác suất 1/3 mỗi seed độc lập vẫn có khả năng bị bỏ sót với năm seed, xác suất minh họa (2/3)^5 khoảng 13.2%. Giả định độc lập này dành cho mô hình xác suất, không phải kết luận thực nghiệm về MockLLM.

## 6. Integrity và ratchet

Bốn trap evaluator_errors_as_nan, dropped_failing_rows, cherry_picked_seeds, loosened_spec đều bị chặn. Gate riêng cho mỗi trap trả exit 1 và lý do INTEGRITY. Output máy sinh được lưu tại src/reports/local_validation.txt.

Integrity kiểm cả baseline và PR về số dòng, tập item/seed, dòng trùng, giá trị không hữu hạn, evaluator_failures, row thiếu boolean và aggregate không khớp row. Kiểm slice tag giữa hai report và giữa các seed của cùng item. Ratchet đối chiếu metric và slice với base-spec trên cùng eval-set version, chặn xóa metric/slice, bỏ blocking/CI, giảm min hoặc tăng max/max_increase.

## 7. Lệnh tái lập

Chạy trong src/.

```powershell
python -m lab9.evalset --build --check
python -m lab9.evalset --v2 --build
python -m lab9.eval --shape swarm --out reports/baseline_v1.json
python -m lab9.eval --shape fixed --out reports/eval_fixed.json
python -m lab9.eval --shape seeded_regression --out reports/eval_seeded_regression.json
python -m lab9.mutation --detect
python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110
python -m lab9.eval --shape slice_regression --spec config/metric_spec_v2.yaml --out reports/eval_slice_regression.json
python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
python -m pytest -q -o addopts=
```

Lượt kiểm toàn bộ repo đạt 361 passed. Test trace tự khôi phục registry sau khi đăng ký variant để không ảnh hưởng test host. Smoke M0 PASS và kiểm baseline/spec cục bộ exit 0.

## 8. Phạm vi, trách nhiệm và giới hạn

Nguyễn Thế Cường là eval owner, xử lý khi gate block bằng việc xem report/trace, sửa trong phạm vi Lab09 rồi chạy lại. Pilot offline trên dữ liệu claims giả lập, chưa triển khai người dùng thật. Commit cuối và PR/GitHub Actions thực hiện ở bước nộp sau khi review.

Swarm Lab08 không xuất event reply. ReplyAmountCorrect trả True với lý do not_applicable cho backend này. Giá trị 1.0 không chứng minh reply đúng và giới hạn tính so sánh với variant có reply. Thiếu reply ở variant khác vẫn fail. Regex chỉ hỗ trợ số nguyên VND và giả định mọi số tiền được nhắc là số đã hoàn, câu có nhiều khoản khác nhau có thể báo nhầm.

MockLLM không đại diện model thật, 14/28 item nhỏ và judge replay công khai chưa có held-out độc lập. Hidden grader và key anchor chỉ giảng viên có. Kết quả công khai chưa bảo đảm tổng quát hóa. Bonus port Inspect AI/DeepEval là tùy chọn, chưa thực hiện.

Thay item/nhãn thì tăng eval_set_version và tạo baseline tương ứng. Đổi metric/ngưỡng thì tăng metric_spec_version. Ngưỡng trên cùng eval-set version chỉ được chặt hơn theo đề.
