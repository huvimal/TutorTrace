import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import store

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def test_submit_review_and_revoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'ui.sqlite3'
            with patch('store.connect', side_effect=lambda *_: store_connect(db)), patch('provider.explain') as provider:
                app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=15).run()
                self.assertEqual(len(app.exception), 0)
                app.text_area[0].set_value('Train học tham số. Validation chọn mô hình. Test đánh giá cuối cùng.')
                next(b for b in app.button if b.label == 'Lưu bài và tạo gợi ý').click().run()
                self.assertEqual(len(app.exception), 0)
                # One rerun to refresh widgets created in the review tab.
                app.run()
                for value in app.number_input:
                    value.set_value(1.0)
                next(t for t in app.text_area if t.label.startswith('Phản hồi')).set_value('Đã đọc; cần giải thích thêm lý do không chọn mô hình bằng test.')
                next(c for c in app.checkbox if c.label.startswith('Tôi đã đọc')).check()
                next(b for b in app.button if b.label == 'Lưu điểm đã duyệt').click().run()
                self.assertEqual(len(app.exception), 0)
                con = store_connect(db)
                self.assertTrue(store.progress(con, 'huni-demo')[0]['reviewed'])
                con.close()
                next(t for t in app.text_area if t.label == 'Câu trả lời mới').set_value('Tôi cần ôn lại.')
                next(b for b in app.button if b.label == 'Lưu bản sửa và hủy điểm cũ').click().run()
                self.assertEqual(len(app.exception), 0)
                con = store_connect(db)
                self.assertFalse(store.progress(con, 'huni-demo')[0]['reviewed'])
                con.close()
                provider.assert_not_called()


store_connect = store.connect
