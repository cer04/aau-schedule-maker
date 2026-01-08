from flask import Flask, render_template, request, jsonify
from utils.parser import extract_schedule
import os

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
def parse_files():
    # Check for files
    pdf_file = request.files.get('pdf_file')
    docx_file = request.files.get('docx_file')
    
    if not pdf_file and not docx_file:
        return jsonify({'error': 'No files uploaded'}), 400

    data = {}
    
    # Paths
    pdf_path = None
    docx_path = None

    try:
        # Process PDF (Doctors)
        if pdf_file and pdf_file.filename != '':
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
            pdf_file.save(pdf_path)
            from utils.parser import parse_doctors_pdf
            data['doctors'] = parse_doctors_pdf(pdf_path)

        # Process Docx (Exams)
        if docx_file and docx_file.filename != '':
            docx_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_file.filename)
            docx_file.save(docx_path)
            from utils.parser import parse_exams_docx
            data['exams'] = parse_exams_docx(docx_path)

        # If both exist, perform matching
        if 'doctors' in data and 'exams' in data:
            from utils.parser import check_availability
            data['matches'] = check_availability(data['exams'], data['doctors'])
            
            # DEBUG: Print first match to console
            if data['matches']:
                first = data['matches'][0]
                print(f"\n{'='*60}")
                print(f"DEBUG: Returning to browser")
                print(f"Course: {first.get('course_name')}")
                print(f"Date: {first.get('date')} ({first.get('day_of_week')})")
                print(f"Available: {len(first.get('available_doctors', []))}")
                ahmed_in = any("احمد" in d and "عماد" in d for d in first.get('available_doctors', []))
                print(f"Ahmed in list: {ahmed_in}")
                print(f"{'='*60}\n")
            
        # Clean up
        if pdf_path and os.path.exists(pdf_path): os.remove(pdf_path)
        if docx_path and os.path.exists(docx_path): os.remove(docx_path)
        
        return jsonify({'success': True, 'data': data})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
