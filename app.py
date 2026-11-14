import json
from pathlib import Path
import streamlit as st
from core import load_course, retrieve
from store import connect, submit, revise, review, attempts, progress, csv_export
from provider import explain

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='TutorTrace', layout='wide')
course = load_course(ROOT / 'data/course.json')
con = connect(ROOT / 'private/tutor.sqlite3')
st.title('TutorTrace')
st.caption('Evidence → Practice → Human review → Progress')
st.info('Mặc định chạy cục bộ. AI giải thích là tùy chọn và chỉ gọi khi bạn bấm nút. Điểm từ khóa chỉ là gợi ý; mã học viên không phải đăng nhập.')
learner = st.sidebar.text_input('Mã học viên demo', 'huni-demo').strip()
api_key = st.sidebar.text_input('Groq API key (tùy chọn)', type='password')
model = st.sidebar.text_input('Groq model', 'openai/gpt-oss-120b')
st.sidebar.caption('Chỉ dùng dữ liệu giả lập. Câu trả lời và điểm được lưu trong SQLite ở thư mục private/.')
tabs = st.tabs(['1. Tài liệu', '2. Bài luyện tập', '3. Duyệt bài', '4. Tiến bộ'])

with tabs[0]:
    question = st.text_input('Tìm nội dung trong tài liệu', 'validation chọn mô hình')
    st.caption('Tìm kiếm theo từ vựng. Các đoạn dưới đây là trích nguyên văn, không phải câu trả lời tổng hợp hay xác nhận đủ bằng chứng.')
    hits = retrieve(course, question)
    if not hits:
        st.warning('Không tìm thấy đoạn trùng từ khóa. Hãy đổi câu hỏi hoặc đọc tài liệu.')
    for item in hits:
        st.subheader(f"[{item['id']}] {item['title']}")
        st.write(item['text'])
    consent = st.checkbox('Cho phép gửi câu hỏi và các đoạn tìm được đến Groq')
    if st.button('AI giải thích từ tài liệu', disabled=not (api_key and consent and hits)):
        try:
            with st.spinner('Đang tạo giải thích...'):
                result = explain(api_key, model, question, hits)
            st.session_state['explanation'] = {'question': question, 'course': course['_fingerprint'], 'result': result}
        except ValueError as exc:
            st.session_state.pop('explanation', None)
            st.error(str(exc))
    saved = st.session_state.get('explanation')
    if saved and saved['question'] == question and saved['course'] == course['_fingerprint']:
        st.caption('Đã kiểm tra ID nguồn và trích nguyên văn. Chưa xác minh rằng nguồn chứng minh từng khẳng định; hãy đối chiếu.')
        result = saved['result']
        if result['abstain']:
            st.warning('AI cho biết tài liệu chưa đủ bằng chứng.')
        for claim in result['claims']:
            st.write(claim['text'])
            st.write(f"[{claim['source_id']}] {claim['quote']}")
    with st.expander('Toàn bộ tài liệu và phiên bản'):
        st.json({'id': course['id'], 'version': course['version'], 'fingerprint': course['_fingerprint']})
        for item in course['passages']:
            st.write(f"[{item['id']}] {item['text']}")

with tabs[1]:
    exercise_id = st.selectbox('Chọn bài', [e['id'] for e in course['exercises']])
    exercise = next(e for e in course['exercises'] if e['id'] == exercise_id)
    st.write(exercise['prompt'])
    st.caption('Bài và rubric do người soạn tạo sẵn; không tự sinh bằng LLM.')
    with st.form('answer_form', clear_on_submit=True):
        answer = st.text_area('Câu trả lời của bạn', max_chars=20000)
        sent = st.form_submit_button('Lưu bài và tạo gợi ý')
        if sent:
            try:
                attempt_id = submit(con, learner, course, exercise, answer)
                st.success(f'Đã lưu bài #{attempt_id}. Sang tab Duyệt bài để xem gợi ý.')
            except ValueError as exc:
                st.error(str(exc))

with tabs[2]:
    items = attempts(con, learner)
    if not items:
        st.write('Chưa có bài cho mã học viên này.')
    else:
        chosen = st.selectbox('Bài đã nộp', [r['id'] for r in items], format_func=lambda n: f'Bài #{n}')
        record = next(r for r in items if r['id'] == chosen)
        st.write(record['answer'])
        if record['fingerprint'] != course['_fingerprint']:
            st.warning('Bài thuộc phiên bản tài liệu khác. Rubric và dẫn chứng dưới đây là bản đã lưu khi nộp.')
        suggestion = json.loads(record['suggestion'])
        st.warning('Từ khóa có thể xuất hiện trong câu sai hoặc phủ định. Không chấp nhận điểm gợi ý nếu chưa đọc bài.')
        st.json(suggestion)
        rubric = json.loads(record['rubric'])
        for row in rubric:
            st.write(f"**{row['label']}** — [{row['source_id']}] {row['quote']}")
        revision = record['revision']
        with st.form(f'review_{chosen}_{revision}'):
            reviewer = st.text_input('Tên người duyệt', 'huni-reviewer')
            points = {r['id']: st.number_input(r['label'], min_value=0.0, max_value=float(r['max_points']), value=0.0, step=0.5, key=f"score_{chosen}_{revision}_{r['id']}") for r in rubric}
            feedback = st.text_area('Phản hồi: giải thích điểm và điều cần sửa')
            checked = st.checkbox('Tôi đã đọc câu trả lời, rubric và trích dẫn')
            approved = st.form_submit_button('Lưu điểm đã duyệt')
            if approved:
                try:
                    if not checked:
                        raise ValueError('Cần đối chiếu bài trước khi duyệt.')
                    review(con, chosen, revision, points, reviewer, feedback)
                    con.close()
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        with st.expander('Sửa câu trả lời — sẽ hủy điểm đã duyệt'):
            with st.form(f'edit_{chosen}_{revision}'):
                edited = st.text_area('Câu trả lời mới', record['answer'], max_chars=20000)
                if st.form_submit_button('Lưu bản sửa và hủy điểm cũ'):
                    try:
                        revise(con, chosen, revision, edited)
                        con.close()
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        if record['review']:
            st.success('Bài đã được duyệt')
            st.json(json.loads(record['review']))

with tabs[3]:
    rows = progress(con, learner)
    if rows:
        st.dataframe([{'exercise': r['exercise'], 'course': r['course'][:12], 'latest_attempt': r['attempt'],
                       'status': 'reviewed' if r['reviewed'] else 'pending',
                       'score': r['grade']['total'] if r['grade'] else None,
                       'max': r['grade']['max_total'] if r['grade'] else None} for r in rows], hide_index=True)
    st.caption('Chỉ hiển thị bài mới nhất theo bài tập và dấu vân tay tài liệu. Bài mới chưa duyệt không kế thừa điểm bài cũ. Điểm giữa các phiên bản không được gộp.')
    st.download_button('Tải CSV điểm đã duyệt', csv_export(con, learner).encode('utf-8'), 'tutortrace-progress.csv', 'text/csv')
con.close()
