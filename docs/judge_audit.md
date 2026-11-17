# Judge audit

## Kết quả calibration

FAIL là lớp positive. Nhãn và lời giải thích được đối chiếu từ hai CSV replay public, các cột human, judge, note và human_failure. Phần nhận định và đề xuất rubric có hỗ trợ của AI, người học cần đọc và xác nhận trước khi nộp.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Dùng để chấm tone trong phạm vi đã calibration |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không | Loại khỏi gate cho đến khi sửa và calibration lại |

| Judge | TP | FP | FN | TN | Tỉ lệ lỗi quan sát | Rogan–Gladen |
|---|---:|---:|---:|---:|---:|---:|
| Tone | 24 | 4 | 6 | 66 | 0.28 | 0.30 |
| Helpful | 9 | 0 | 21 | 70 | 0.09 | 0.30 |

## Audit 10 trường hợp bất đồng

Kết luận dưới đây theo bối cảnh và quy ước được ghi trong CSV. Các số ledger của Helpful được dẫn từ cột note của tập calibration, chưa được xác minh độc lập bằng SQLite. Không dùng world Lab08 để thay thế bối cảnh của các mẫu replay này.

| # | Case | Judge nói | Người nói | Ai đúng? | Bằng chứng và hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Người | Câu dùng “em”, “nha”, “check giúp em” được note xác định là quá suồng sã với khách. Thêm tiêu chí mức độ trang trọng phù hợp bối cảnh và ví dụ phân biệt thân thiện với suồng sã. Tránh quy tắc cấm từ đơn lẻ trong mọi hoàn cảnh. |
| 2 | H-017 | PASS | FAIL | Người | Note cho biết khách lớn tuổi, cách gọi “bạn ơi” và “nha” không phù hợp. Rubric cần xét quan hệ xưng hô và ngữ cảnh tuổi khách. Nếu thiếu ngữ cảnh thì chuyển human review, không đoán tuổi từ câu trả lời. |
| 3 | H-029 | PASS | FAIL | Người | “Không cần nhắn thêm” mang giọng ngăn cản hoặc ra lệnh dù mở đầu “Dạ, vui lòng”. Rubric phải đánh giá toàn câu, bổ sung tiêu chí tránh phủ nhận quyền hỏi tiếp của khách. |
| 4 | H-042 | FAIL | PASS | Người | Câu ngắn, có “Dạ”, “ạ”, thông báo và thời gian chờ. Theo note, judge phạt thiếu xin lỗi. Bỏ điều kiện bắt buộc xin lỗi trong mọi câu, thêm ví dụ ngắn vẫn đạt tone. Chỉ kết luận về tone, không xác minh số tiền của câu này. |
| 5 | H-051 | FAIL | PASS | Người | Note ghi thuật ngữ “refund” được CS LogiX cho phép. Bổ sung thuật ngữ được phép, tránh đánh FAIL chỉ vì xuất hiện tiếng Anh. Kiểm tra tính dễ hiểu theo ngữ cảnh. |
| 6 | HL-015 | PASS | FAIL | Người | Reply báo 55000, note ghi ledger 40000, lệch +15000 VND. Yêu cầu đối chiếu số tiền với ledger bằng code, sai tiền phải FAIL dù câu lịch sự. |
| 7 | HL-016 | PASS | FAIL | Người | Reply dài và nhiều lời xin lỗi nhưng báo 55000, note ledger 35000, lệch +20000 VND. Đặt tính đúng nghiệp vụ là điều kiện bắt buộc, không cho lời xin lỗi bù lỗi số tiền. |
| 8 | HL-020 | PASS | FAIL | Người | Reply báo 90000, note ledger 120000, lệch −30000 VND. Rubric kiểm cả báo thiếu và báo thừa, so chính xác số nguyên VND sau chuẩn hóa cách viết. |
| 9 | HL-028 | PASS | FAIL | Người | Reply lặp lời xin lỗi, báo 50000 trong khi note ledger 35000, lệch +15000 VND. Kiểm đúng tiền trước khi chấm mức hữu ích, thêm ví dụ dài và lịch sự nhưng sai dữ kiện. |
| 10 | HL-035 | PASS | FAIL | Người | Reply có lời xin lỗi và kêu gọi tiếp tục ủng hộ nhưng báo 50000, note ledger 35000, lệch +15000 VND. Tách tiêu chí đúng tiền, đúng tác vụ và hướng dẫn tiếp theo, không dùng mức trôi chảy làm bằng chứng đúng nghiệp vụ. |

## Đề xuất cập nhật rubric và kiểm chứng lại

1. Tone xét toàn bộ cách diễn đạt, xưng hô và mức trang trọng theo ngữ cảnh. Không dùng sự hiện diện của “Dạ”, “ạ” hoặc lời xin lỗi làm điều kiện đủ. Không phạt tự động câu ngắn hoặc thuật ngữ đã được cho phép.
2. Helpful cần nhận claim, kết quả xử lý và dữ liệu ledger có thẩm quyền. Kiểm tra tiền và approval bằng code, đối chiếu số được thông báo với số thực ghi. Khi thiếu căn cứ phải chuyển người đánh giá thay vì đoán.
3. Bổ sung ví dụ đối lập gồm câu ngắn đúng dữ kiện, câu dài lịch sự nhưng sai tiền, và câu có lời mở đầu lịch sự nhưng phần sau ra lệnh. Không coi độ dài là thước đo helpfulness.
4. Sau khi sửa rubric, thu thập nhãn người mới trên held-out độc lập, chạy lại confusion matrix, precision, recall và kappa theo cùng sàn. Các đề xuất trên chưa được thử với judge mới vì backend hiện là replay cố định.

## Kết luận

Tone đạt cả ba sàn trên 100 mẫu, nhưng vẫn có 4 báo nhầm và 6 bỏ sót. Helpful chỉ bắt 9/30 lỗi và bỏ sót 21/30, tương ứng recall 0.30, kappa 0.375. Precision 1.0 chỉ phản ánh chín trường hợp judge đã gắn FAIL đều đúng, không bù được số lỗi bỏ sót, vì vậy Helpful bị loại khỏi gate.

Hiệu chỉnh Rogan–Gladen đưa tỉ lệ lỗi quan sát của cả hai về 0.30. Đây là hiệu chỉnh tỉ lệ tổng thể, không sửa các quyết định sai trên từng mẫu. Chỉ số được tính trên cùng dữ liệu calibration nên chưa chứng minh hiệu năng trên dữ liệu mới.

Rủi ro còn lại là CSV replay đã công khai, số mẫu chỉ 100 cho mỗi tiêu chí, nhãn người và note chưa được adjudication độc lập trong bài này. Nếu dùng các bất đồng để sửa rubric rồi đánh giá lại trên chính tập đó, kết quả có thể lạc quan. Tiền, approval và tính nhất quán reply/ledger cần grader code dù Tone đã qua calibration.

## Lệnh tái hiện

Chạy trong src/.

```powershell
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
```

Tone phải PASS floors, exit 0. Helpful phải FAIL floors, exit 1. Các kết quả calibration trong bảng lấy từ output thực tế người học đã chạy. Nguồn audit là src/data/eval/judge_tone_public.csv và src/data/eval/judge_helpful_public.csv.
