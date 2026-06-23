// js/predictions.js
document.addEventListener('DOMContentLoaded', async () => {
    const patientSelect = document.getElementById('patient-select');
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

    // Load patients for dropdown
    async function loadPatients() {
        try {
            // Using a large page size to get all/most patients for dropdown
            // In a real prod environment, we would use a search API with Select2 or similar
            const data = await apiFetch('/patients?page=1&page_size=100');
            
            patientSelect.innerHTML = '<option value="">-- Chọn bệnh nhân --</option>';
            data.items.forEach(p => {
                const option = document.createElement('option');
                option.value = p.id;
                option.textContent = `${p.patient_code} - ${p.full_name}`;
                if (p.id === preselectedPatientId) {
                    option.selected = true;
                }
                patientSelect.appendChild(option);
            });
        } catch (error) {
            patientSelect.innerHTML = `<option value="">Lỗi tải danh sách: ${error.message}</option>`;
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
        
        const patientId = patientSelect.value;
        const file = fileInput.files[0];

        if (!patientId || !file) {
            formError.textContent = "Vui lòng chọn bệnh nhân và tải ảnh lên.";
            formError.classList.remove('hidden');
            return;
        }

        formError.classList.add('hidden');
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
            
            // Set images with token (for FastAPI serving static files or endpoints that might need auth, but typically static paths don't have token auth in this basic setup. Assuming static files are publicly accessible or handled by cookies. If they are protected APIs, we need to fetch them as blob. Let's try simple src first).
            // Usually, FastAPI static files don't require JWT. We will just set the SRC to the backend URL.
            const baseUrl = 'http://localhost:8000';
            resOriginalImg.src = `${baseUrl}/${result.mri_image_path}`;
            resGradcamImg.src = result.gradcam_image_path ? `${baseUrl}/${result.gradcam_image_path}` : '';

            resultContainer.classList.remove('hidden');
            resultContainer.scrollIntoView({ behavior: 'smooth' });

        } catch (error) {
            formError.textContent = error.message;
            formError.classList.remove('hidden');
        } finally {
            btnPredict.disabled = false;
            btnPredict.textContent = 'Thực hiện Chẩn đoán';
        }
    });

    await loadPatients();
});
