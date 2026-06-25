// js/predictions.js
document.addEventListener('DOMContentLoaded', async () => {
    const patientSearchInput = document.getElementById('patient-search');
    const patientIdInput = document.getElementById('patient-id');
    const patientSuggestions = document.getElementById('patient-suggestions');
    const selectedPatientCard = document.getElementById('selected-patient');
    const selectedPatientName = document.getElementById('selected-patient-name');
    const selectedPatientMeta = document.getElementById('selected-patient-meta');
    const btnChangePatient = document.getElementById('btn-change-patient');
    const fileInput = document.getElementById('mri-image');
    const previewContainer = document.getElementById('preview-container');
    const previewImage = document.getElementById('preview-image');
    const form = document.getElementById('prediction-form');
    const btnPredict = document.getElementById('btn-predict');
    const formError = document.getElementById('form-error');

    const resultContainer = document.getElementById('result-container');
    const resClass = document.getElementById('res-class');
    const resConfidence = document.getElementById('res-confidence');
    const resOriginalImg = document.getElementById('res-original-img');
    const resGradcamImg = document.getElementById('res-gradcam-img');

    // Parse URL parameter
    const urlParams = new URLSearchParams(window.location.search);
    const preselectedPatientId = urlParams.get('patient_id');

    let searchTimer = null;
    let searchRequestId = 0;
    let searchResults = [];
    let activeSuggestionIndex = -1;
    let selectedPatient = null;

    function formatDate(value) {
        if (!value) return 'Chưa cập nhật ngày sinh';
        const date = new Date(value);
        return Number.isNaN(date.getTime())
            ? value
            : date.toLocaleDateString('vi-VN');
    }

    function setSuggestionsVisible(visible) {
        patientSuggestions.classList.toggle('hidden', !visible);
        patientSearchInput.setAttribute('aria-expanded', String(visible));
    }

    function renderSuggestionMessage(message, isError = false) {
        patientSuggestions.innerHTML = '';
        const element = document.createElement('div');
        element.className = `patient-suggestion-message${isError ? ' text-error' : ''}`;
        element.textContent = message;
        patientSuggestions.appendChild(element);
        setSuggestionsVisible(true);
    }

    function updateActiveSuggestion() {
        const options = patientSuggestions.querySelectorAll('.patient-suggestion-item');
        options.forEach((option, index) => {
            const active = index === activeSuggestionIndex;
            option.classList.toggle('active', active);
            option.setAttribute('aria-selected', String(active));
        });
    }

    function selectPatient(patient) {
        searchRequestId += 1;
        clearTimeout(searchTimer);
        selectedPatient = patient;
        patientIdInput.value = patient.id;
        patientSearchInput.value = `${patient.patient_code} - ${patient.full_name}`;
        selectedPatientName.textContent = `${patient.patient_code} - ${patient.full_name}`;

        const details = [
            patient.date_of_birth ? `Ngày sinh: ${formatDate(patient.date_of_birth)}` : null,
            patient.phone_number ? `SĐT: ${patient.phone_number}` : null
        ].filter(Boolean);
        selectedPatientMeta.textContent = details.join(' • ') || 'Hồ sơ đã được chọn';

        selectedPatientCard.classList.remove('hidden');
        activeSuggestionIndex = -1;
        setSuggestionsVisible(false);
        formError.classList.add('hidden');
    }

    function clearSelectedPatient({ clearText = true, focus = false } = {}) {
        searchRequestId += 1;
        clearTimeout(searchTimer);
        selectedPatient = null;
        patientIdInput.value = '';
        selectedPatientCard.classList.add('hidden');
        if (clearText) patientSearchInput.value = '';
        if (focus) patientSearchInput.focus();
    }

    function renderSuggestions(items) {
        searchResults = items;
        activeSuggestionIndex = -1;
        patientSuggestions.innerHTML = '';

        if (!items.length) {
            renderSuggestionMessage('Không tìm thấy hồ sơ bệnh nhân phù hợp.');
            return;
        }

        items.forEach((patient, index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'patient-suggestion-item';
            button.setAttribute('role', 'option');
            button.setAttribute('aria-selected', 'false');
            button.dataset.index = String(index);

            const main = document.createElement('span');
            main.className = 'patient-suggestion-main';

            const code = document.createElement('strong');
            code.textContent = patient.patient_code;
            const name = document.createElement('span');
            name.textContent = patient.full_name;
            main.append(code, name);

            const meta = document.createElement('small');
            const metaParts = [
                patient.date_of_birth ? `Ngày sinh: ${formatDate(patient.date_of_birth)}` : null,
                patient.phone_number ? `SĐT: ${patient.phone_number}` : null
            ].filter(Boolean);
            meta.textContent = metaParts.join(' • ') || 'Chưa có thông tin liên hệ';

            button.append(main, meta);
            button.addEventListener('mousedown', (event) => event.preventDefault());
            button.addEventListener('click', () => selectPatient(patient));
            patientSuggestions.appendChild(button);
        });

        setSuggestionsVisible(true);
    }

    async function searchPatients(keyword = '') {
        const requestId = ++searchRequestId;
        renderSuggestionMessage('Đang tìm hồ sơ bệnh nhân...');

        try {
            let endpoint = '/patients?page=1&page_size=8';
            if (keyword) endpoint += `&keyword=${encodeURIComponent(keyword)}`;
            const data = await apiFetch(endpoint);
            if (requestId !== searchRequestId) return;
            renderSuggestions(data.items || []);
        } catch (error) {
            if (requestId !== searchRequestId) return;
            renderSuggestionMessage(`Không thể tìm bệnh nhân: ${error.message}`, true);
        }
    }

    patientSearchInput.addEventListener('focus', () => {
        if (!selectedPatient) searchPatients(patientSearchInput.value.trim());
    });

    patientSearchInput.addEventListener('input', () => {
        if (selectedPatient) clearSelectedPatient({ clearText: false });
        clearTimeout(searchTimer);
        const keyword = patientSearchInput.value.trim();
        searchTimer = setTimeout(() => searchPatients(keyword), 250);
    });

    patientSearchInput.addEventListener('keydown', (event) => {
        const options = patientSuggestions.querySelectorAll('.patient-suggestion-item');
        if (patientSuggestions.classList.contains('hidden') || !options.length) {
            if (event.key === 'ArrowDown') searchPatients(patientSearchInput.value.trim());
            return;
        }

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            activeSuggestionIndex = (activeSuggestionIndex + 1) % options.length;
            updateActiveSuggestion();
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            activeSuggestionIndex = activeSuggestionIndex <= 0
                ? options.length - 1
                : activeSuggestionIndex - 1;
            updateActiveSuggestion();
        } else if (event.key === 'Enter' && activeSuggestionIndex >= 0) {
            event.preventDefault();
            selectPatient(searchResults[activeSuggestionIndex]);
        } else if (event.key === 'Escape') {
            setSuggestionsVisible(false);
        }
    });

    patientSearchInput.addEventListener('blur', () => {
        window.setTimeout(() => setSuggestionsVisible(false), 150);
    });

    btnChangePatient.addEventListener('click', () => {
        clearSelectedPatient({ focus: true });
    });

    async function loadPreselectedPatient() {
        if (!preselectedPatientId) return;
        try {
            const patient = await apiFetch(`/patients/${preselectedPatientId}`);
            selectPatient(patient);
        } catch (error) {
            clearSelectedPatient();
            formError.textContent = `Không thể tải hồ sơ bệnh nhân đã chọn: ${error.message}`;
            formError.classList.remove('hidden');
        }
    }

    // Image preview
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            // Check size (10MB max)
            if (file.size > 10 * 1024 * 1024) {
                alert('Kích thước ảnh quá lớn. Vui lòng chọn ảnh < 10MB.');
                this.value = '';
                previewContainer.classList.add('hidden');
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                previewImage.src = e.target.result;
                previewContainer.classList.remove('hidden');
            }
            reader.readAsDataURL(file);
            
            // Hide previous results
            resultContainer.classList.add('hidden');
        } else {
            previewContainer.classList.add('hidden');
        }
    });

    const labelMap = {
        'glioma_tumor': { label: 'Glioma (U tế bào thần kinh đệm)', badge: 'badge-glioma' },
        'meningioma_tumor': { label: 'Meningioma (U màng não)', badge: 'badge-meningioma' },
        'pituitary_tumor': { label: 'Pituitary (U tuyến yên)', badge: 'badge-pituitary' },
        'no_tumor': { label: 'Không có u', badge: 'badge-notumor' }
    };

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const patientId = patientIdInput.value;
        const file = fileInput.files[0];

        if (!patientId) {
            formError.textContent = 'Vui lòng tìm và chọn đúng một hồ sơ bệnh nhân trong danh sách gợi ý.';
            formError.classList.remove('hidden');
            patientSearchInput.focus();
            return;
        }

        if (!file) {
            formError.textContent = 'Vui lòng tải ảnh MRI lên.';
            formError.classList.remove('hidden');
            return;
        }

        formError.classList.add('hidden');
        resultContainer.classList.add('hidden');
        btnPredict.disabled = true;
        btnPredict.textContent = 'Đang phân tích, vui lòng chờ...';

        const formData = new FormData();
        formData.append('patient_id', patientId);
        formData.append('mri_image', file);

        try {
            const result = await apiFetch('/predictions', {
                method: 'POST',
                body: formData
            });

            // Display results
            const mappedClass = labelMap[result.predicted_class] || { label: result.predicted_class, badge: '' };
            
            resClass.textContent = mappedClass.label;
            resClass.className = `badge ${mappedClass.badge}`;
            resClass.style.fontSize = '1.25rem';
            resClass.style.marginTop = '0.5rem';

            resConfidence.textContent = `${(result.confidence * 100).toFixed(2)}%`;
            
            // Ảnh được truy cập qua Nginx cùng origin với frontend.
            const buildStorageUrl = (path) => `/${String(path).replace(/^\/+/, '')}`;
            resOriginalImg.src = buildStorageUrl(result.mri_image_path);
            resGradcamImg.src = result.gradcam_image_path ? buildStorageUrl(result.gradcam_image_path) : '';

            resultContainer.classList.remove('hidden');
            resultContainer.scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            resultContainer.classList.add('hidden');
            formError.textContent = error.message;
            formError.classList.remove('hidden');
        } finally {
            btnPredict.disabled = false;
            btnPredict.textContent = 'Thực hiện Chẩn đoán';
        }
    });

    await loadPreselectedPatient();
});
