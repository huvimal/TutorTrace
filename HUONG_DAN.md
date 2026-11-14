# Chạy và kiểm tra TutorTrace

## 1. Cài đặt

Mở PowerShell:

```powershell
cd "C:\Users\LOQ\Documents\Codex\2026-11-06\cj\outputs\TutorTrace"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -X utf8 evaluate.py --output reports/my-evaluation-v1.json
```

Đọc báo cáo:

```powershell
Get-Content reports/my-evaluation-v1.json -Encoding utf8
```

Kỳ vọng: retrieval_passed=5/5 và grading_passed=4/4. Đây là fixture nhỏ tự soạn, không phải độ chính xác chấm bài thực tế.

## 2. Mở ứng dụng

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8512
```

Mở http://127.0.0.1:8512. Giữ cửa sổ PowerShell chạy. Nếu cổng bận, đổi sang 8513 và mở đúng cổng mới.

## 3. Tìm tài liệu

Giữ mã học viên `huni-demo`. Tab Tài liệu, nhập `validation chọn mô hình`: đoạn S1 phải đứng đầu. Nhập `địa chất núi lửa`: không có đoạn phù hợp. Bộ tìm kiếm dùng từ khóa, không hiểu mọi câu diễn đạt lại.

Nếu muốn thử AI, nhập Groq key trong thanh bên, dùng model có quyền truy cập, tích cho phép gửi câu hỏi và các đoạn trích rồi bấm AI giải thích. Chỉ thao tác này gọi API. Không gửi key trong ảnh hoặc chat. Khi thành công, đối chiếu từng giải thích với nguồn; trích đúng nguyên văn chưa đảm bảo kết luận đúng. API lỗi không ảnh hưởng bài và điểm lưu cục bộ.

## 4. Nộp bài

Tab Bài luyện tập, chọn E1 và nhập:

```text
Train học tham số. Validation chọn mô hình. Test đánh giá cuối cùng.
```

Bấm Lưu bài và tạo gợi ý. Tab Duyệt bài, chọn số bài vừa lưu. Gợi ý dự kiến 3/3. Đây chỉ là gợi ý từ khóa: câu này còn thiếu giải thích lý do không chọn mô hình bằng test, vì thế người duyệt cần viết phản hồi và cân nhắc điểm thực tế.

## 5. Duyệt và xuất điểm

Đọc bài, từng tiêu chí và trích dẫn. Điền điểm (không tự điền bằng gợi ý), tên người duyệt, phản hồi cụ thể. Tích đã đối chiếu rồi lưu điểm. Tab Tiến bộ hiển thị reviewed; tải CSV để mở bằng Excel.

## 6. Kiểm tra hủy điểm cũ

Quay lại Duyệt bài, mở phần Sửa câu trả lời. Đổi thành `Tôi cần ôn lại validation.` rồi lưu. Tab Tiến bộ phải trở về pending, điểm cũ không được xuất. Điểm chỉ xuất lại sau một lượt duyệt mới.

Nếu nộp thêm E1, bài mới nhất quyết định trạng thái; bài mới chưa duyệt không được kế thừa điểm bài trước. Mã học viên khác có danh sách khác nhưng đây không phải phân quyền bảo mật.

## 7. Hiểu giới hạn của gợi ý

Thử một bài mới với câu `Train không học tham số`. Gợi ý vẫn có thể cộng 1 điểm vì khớp từ khóa; người duyệt phải sửa về 0 cho tiêu chí đó và giải thích lỗi. Đây là giới hạn được cố ý giữ rõ và kiểm thử, không phải chấm ngữ nghĩa bằng AI.

Không dùng điểm demo để đánh giá người học thật. Không gộp kết quả của các phiên bản tài liệu để kết luận năng lực.

## 8. Mở rộng nội dung

Sửa `data/course.json` bằng trình soạn thảo UTF-8. Mỗi passage, exercise và rubric cần ID riêng. Rubric có các nhóm concepts: mỗi nhóm cần một cụm khớp; các cụm trong một nhóm là lựa chọn thay thế. Quote phải là đoạn nguyên văn từ source_id. Sau khi sửa, chạy lại test và cập nhật fixture có chủ đích; không sửa đáp án chỉ để che lỗi. Dấu vân tay khóa nội dung thay đổi sẽ tách phiên bản tiến bộ.
