document.addEventListener('DOMContentLoaded', () => {
    // State
    let pdfFile = null;
    let docxFile = null;

    // Elements
    const dropZonePdf = document.getElementById('dropZonePdf');
    const fileInputPdf = document.getElementById('fileInputPdf');
    const statusPdf = document.getElementById('statusPdf');

    const dropZoneDocx = document.getElementById('dropZoneDocx');
    const fileInputDocx = document.getElementById('fileInputDocx');
    const statusDocx = document.getElementById('statusDocx');

    const processBtn = document.getElementById('processBtn');
    const loadingState = document.getElementById('loadingState');
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');
    const uploadSection = document.getElementById('uploadSection');
    const resultsSection = document.getElementById('resultsSection');
    const resetBtn = document.getElementById('resetBtn');

    // Setup Drop Zones
    setupDropZone(dropZonePdf, fileInputPdf, 'pdf', (file) => {
        pdfFile = file;
        updateStatus(statusPdf, true);
        checkReady();
    });

    setupDropZone(dropZoneDocx, fileInputDocx, 'docx', (file) => {
        docxFile = file;
        updateStatus(statusDocx, true);
        checkReady();
    });

    function setupDropZone(zone, input, type, callback) {
        zone.addEventListener('click', () => input.click());

        input.addEventListener('change', (e) => {
            if (e.target.files.length > 0) processFile(e.target.files[0]);
        });

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            zone.addEventListener(eventName, () => zone.classList.add('dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            zone.addEventListener(eventName, () => zone.classList.remove('dragover'), false);
        });

        zone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            if (dt.files.length > 0) processFile(dt.files[0]);
        });

        function processFile(file) {
            if (type === 'pdf' && file.type !== 'application/pdf') {
                showError('Please upload a PDF file for the Doctor Schedule.');
                return;
            }
            if (type === 'docx' && !file.name.match(/\.(docx|doc)$/i)) {
                showError('Please upload a Word file for the Exam Schedule.');
                return;
            }
            showError(''); // Clear error
            callback(file);
        }
    }

    function updateStatus(el, selected) {
        if (selected) el.classList.remove('hidden');
        else el.classList.add('hidden');
    }

    function checkReady() {
        if (pdfFile && docxFile) {
            processBtn.removeAttribute('disabled');
        } else {
            // Optional: If you want to allow single file processing, logic here. 
            // But user request is specifically for matching.
            if (pdfFile || docxFile) {
                // processBtn.removeAttribute('disabled'); // Uncomment to allow single
            }
        }
    }

    function showError(msg) {
        if (!msg) {
            errorMessage.classList.add('hidden');
            return;
        }
        errorMessage.classList.remove('hidden');
        errorText.textContent = msg;
    }

    processBtn.addEventListener('click', () => {
        if (!pdfFile && !docxFile) return;

        // UI Loading
        processBtn.classList.add('hidden');
        document.querySelector('.upload-grid').classList.add('hidden');
        loadingState.classList.remove('hidden');

        const formData = new FormData();
        if (pdfFile) formData.append('pdf_file', pdfFile);
        if (docxFile) formData.append('docx_file', docxFile);

        fetch('/parse', {
            method: 'POST',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                renderResults(data.data);
            })
            .catch(err => {
                showError(err.message);
                // Reset UI slightly
                loadingState.classList.add('hidden');
                processBtn.classList.remove('hidden');
                document.querySelector('.upload-grid').classList.remove('hidden');
            });
    });

    function renderResults(data) {
        loadingState.classList.add('hidden');
        uploadSection.classList.add('hidden');
        resultsSection.classList.remove('hidden');

        const container = document.querySelector('.results-section');
        // Clear previous cards, preserve header/reset button
        const existingCards = container.querySelectorAll('.instructor-card');
        existingCards.forEach(c => c.remove());

        // Helper to add card
        const createCard = (title, contentHTML) => {
            const card = document.createElement('div');
            card.className = 'instructor-card';
            card.style.marginBottom = '30px';
            card.innerHTML = `
                <div class="card-header">
                    <h2>${title}</h2>
                </div>
                <div class="schedule-grid" style="display:block; padding: 1.5rem;">
                    ${contentHTML}
                </div>
            `;
            container.appendChild(card);
        };

        // 1. Matches (The main goal)
        if (data.matches) {
            let html = '';
            data.matches.forEach(exam => {
                const docs = exam.available_doctors || [];
                const docsBadges = docs.length > 0
                    ? docs.map(d => `<span class="badge" style="background:#e0f2f1; color:#00695c; margin:2px;">${d}</span>`).join(' ')
                    : '<span style="color:#e74c3c; font-weight: bold;">⚠️ No Doctors Available</span>';

                html += `
                    <div class="item-card" style="margin-bottom:1rem;">
                        <div class="item-header">
                            <strong>${exam.course_name}</strong>
                            <span>${exam.date || ''} (${exam.day_of_week || '?'})</span>
                        </div>
                        <div style="margin-bottom: 8px;">
                            <i class="ph ph-clock"></i> ${exam.raw_time}
                        </div>
                        ${exam.room ? `<div style="margin-bottom: 8px;"><i class="ph ph-building"></i> القاعة: ${exam.room}</div>` : ''}
                        ${exam.section ? `<div style="margin-bottom: 8px;"><i class="ph ph-user-list"></i> الشعبة: ${exam.section}</div>` : ''}
                        <div>
                            <strong>Available Proctors:</strong>
                            <div style="margin-top:5px;">${docsBadges}</div>
                        </div>
                    </div>
                `;
            });
            createCard("Exam Proctoring Schedule", html);
        }

        // 2. Fallback: Doctors List (PDF Only)
        else if (data.doctors) {
            // Reuse previous rendering logic for doctors if needed, or simple dump
            // Only show if no matches
            createCard("Doctors Schedule", "<p>PDF Processed. Upload Exam docx to see matching.</p>");
        }
    }

    resetBtn.addEventListener('click', () => {
        // Reload page or reset state deeply
        window.location.reload();
    });
});
