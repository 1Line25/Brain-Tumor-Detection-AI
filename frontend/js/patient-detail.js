document.addEventListener('DOMContentLoaded', () => {
    const pageSize = 10;
    let currentPage = 1;

    const params = new URLSearchParams(window.location.search);
    const patientId = params.get('patient_id');
    const patientHeading = document.getElementById('patient-heading');
    const patientInfo = document.getElementById('patient-info');
    const historyContainer = document.getElementById('prediction-history');
    const historySummary = document.getElementById('history-summary');
    const pagination = document.getElementById('detail-pagination');
    const errorCard = document.getElementById('detail-error');
    const newPredictionButton = document.getElementById('btn-new-prediction');

    const sexMap = {
        male: 'Nam',
        female: 'Nữ',
        other: 'Khác',
        unknown: 'Chưa cập nhật'
    };

    const labelMap = {
        glioma_tumor: { label: 'Glioma (U tế bào thần kinh đệm)', badge: 'badge-glioma' },
        meningioma_tumor: { label: 'Meningioma (U màng não)', badge: 'badge-meningioma' },
        pituitary_tumor: { label: 'Pituitary (U tuyến yên)', badge: 'badge-pituitary' },
        no_tumor: { label: 'Không phát hiện u', badge: 'badge-notumor' }
    };

    function escapeHtml(value) {
        const element = document.createElement('div');
        element.textContent = value == null ? '' : String(value);
        return element.innerHTML;
    }

    function formatDate(value, includeTime = false) {
        if (!value) return '-';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return escapeHtml(value);
        return includeTime
            ? date.toLocaleString('vi-VN')
            : date.toLocaleDateString('vi-VN');
    }

    function buildStorageUrl(path) {
        return `/${String(path).replace(/^\/+/, '')}`;
    }

    function showError(message) {
        errorCard.querySelector('.card-body').textContent = message;
        errorCard.classList.remove('hidden');
    }

    async function loadPatient() {
        const patient = await apiFetch(`/patients/${patientId}`);
        patientHeading.textContent = `${patient.patient_code} - ${patient.full_name}`;
        document.title = `${patient.patient_code} - Chi tiết Bệnh nhân`;
        newPredictionButton.href = `prediction.html?patient_id=${patient.id}`;

        const creator = patient.created_by_user
            ? (patient.created_by_user.full_name || patient.created_by_user.username)
            : '-';

        patientInfo.innerHTML = `
            <div class="patient-info-item">
                <span>Mã bệnh nhân</span>
                <strong>${escapeHtml(patient.patient_code)}</strong>
            </div>
            <div class="patient-info-item">
                <span>Họ và tên</span>
                <strong>${escapeHtml(patient.full_name)}</strong>
            </div>
            <div class="patient-info-item">
                <span>Ngày sinh</span>
                <strong>${formatDate(patient.date_of_birth)}</strong>
            </div>
            <div class="patient-info-item">
                <span>Giới tính</span>
                <strong>${escapeHtml(sexMap[patient.sex] || patient.sex)}</strong>
            </div>
            <div class="patient-info-item">
                <span>Số điện thoại</span>
                <strong>${escapeHtml(patient.phone_number || '-')}</strong>
            </div>
            <div class="patient-info-item">
                <span>Người tạo hồ sơ</span>
                <strong>${escapeHtml(creator)}</strong>
            </div>
            <div class="patient-info-item patient-info-notes">
                <span>Ghi chú</span>
                <strong>${escapeHtml(patient.notes || 'Không có ghi chú')}</strong>
            </div>
        `;
    }

    function renderImages(prediction) {
        if (prediction.files_deleted) {
            return `
                <div class="prediction-files-unavailable">
                    Ảnh MRI và Grad-CAM đã hết thời hạn lưu trữ. Kết quả dự đoán vẫn được giữ lại.
                </div>
            `;
        }

        const originalImage = prediction.mri_image_path
            ? `<img src="${buildStorageUrl(prediction.mri_image_path)}" alt="Ảnh MRI gốc" loading="lazy">`
            : '<div class="image-placeholder">Không có ảnh MRI</div>';
        const gradcamImage = prediction.gradcam_image_path
            ? `<img src="${buildStorageUrl(prediction.gradcam_image_path)}" alt="Ảnh Grad-CAM" loading="lazy">`
            : '<div class="image-placeholder">Không có ảnh Grad-CAM</div>';

        return `
            <div class="prediction-images">
                <figure>
                    ${originalImage}
                    <figcaption>Ảnh MRI gốc</figcaption>
                </figure>
                <figure>
                    ${gradcamImage}
                    <figcaption>Vùng chú ý Grad-CAM</figcaption>
                </figure>
            </div>
        `;
    }

    function renderProbabilities(probabilities) {
        if (!probabilities) return '';

        const rows = Object.entries(probabilities)
            .sort((a, b) => b[1] - a[1])
            .map(([key, value]) => {
                const label = labelMap[key]?.label || key;
                const percentage = `${(Number(value) * 100).toFixed(2)}%`;
                return `<span><span>${escapeHtml(label)}</span><strong>${percentage}</strong></span>`;
            })
            .join('');

        return `<div class="prediction-probabilities">${rows}</div>`;
    }

    function renderHistory(items) {
        if (!items || items.length === 0) {
            historyContainer.innerHTML = `
                <div class="empty-history">
                    <strong>Chưa có lần dự đoán MRI nào</strong>
                    <p>Bệnh nhân này chưa có ảnh và kết quả dự đoán trong hệ thống.</p>
                    <a href="prediction.html?patient_id=${encodeURIComponent(patientId)}" class="btn btn-primary">Chẩn đoán MRI</a>
                </div>
            `;
            return;
        }

        historyContainer.innerHTML = items.map((prediction) => {
            const mappedClass = labelMap[prediction.predicted_class] || {
                label: prediction.predicted_class || 'Không có kết quả',
                badge: ''
            };
            const doctor = prediction.doctor
                ? (prediction.doctor.full_name || prediction.doctor.username)
                : '-';
            const isSuccess = prediction.status === 'success';
            const confidence = prediction.confidence == null
                ? '-'
                : `${(prediction.confidence * 100).toFixed(2)}%`;

            return `
                <article class="prediction-history-item">
                    <div class="prediction-history-top">
                        <div>
                            <span class="prediction-date">${formatDate(prediction.created_at, true)}</span>
                            <div class="prediction-doctor">Thực hiện bởi: ${escapeHtml(doctor)}</div>
                        </div>
                        <span class="prediction-status ${isSuccess ? 'success' : 'failed'}">
                            ${isSuccess ? 'Thành công' : 'Thất bại'}
                        </span>
                    </div>
                    <div class="prediction-result-row">
                        <div>
                            <span>Kết quả dự đoán</span>
                            <strong class="badge ${mappedClass.badge}">${escapeHtml(mappedClass.label)}</strong>
                        </div>
                        <div>
                            <span>Độ tin cậy</span>
                            <strong class="confidence-value">${confidence}</strong>
                        </div>
                    </div>
                    ${isSuccess ? renderImages(prediction) : `
                        <div class="prediction-files-unavailable text-error">
                            Lần dự đoán này không hoàn tất nên không có kết quả ảnh Grad-CAM.
                        </div>
                    `}
                    ${isSuccess ? renderProbabilities(prediction.probabilities) : ''}
                </article>
            `;
        }).join('');
    }

    function renderPagination(page, totalPages) {
        pagination.innerHTML = '';
        if (totalPages <= 1) return;

        const createButton = (label, targetPage, disabled = false, active = false) => {
            const button = document.createElement('button');
            button.className = `page-item${active ? ' active' : ''}`;
            button.textContent = label;
            button.disabled = disabled;
            button.addEventListener('click', () => {
                currentPage = targetPage;
                loadHistory(currentPage);
            });
            return button;
        };

        pagination.appendChild(createButton('Trước', page - 1, page === 1));
        for (let index = 1; index <= totalPages; index += 1) {
            pagination.appendChild(createButton(String(index), index, false, index === page));
        }
        pagination.appendChild(createButton('Sau', page + 1, page === totalPages));
    }

    async function loadHistory(page = 1) {
        historyContainer.innerHTML = '<div class="detail-loading">Đang tải lịch sử...</div>';
        pagination.innerHTML = '';

        try {
            const data = await apiFetch(
                `/predictions?page=${page}&page_size=${pageSize}&patient_id=${encodeURIComponent(patientId)}`
            );
            historySummary.textContent = `${data.total} lần dự đoán`;
            renderHistory(data.items);
            renderPagination(data.page, data.total_pages);
        } catch (error) {
            historySummary.textContent = 'Không thể tải lịch sử';
            historyContainer.innerHTML = `<div class="text-error">${escapeHtml(error.message)}</div>`;
        }
    }

    async function init() {
        if (!patientId) {
            patientHeading.textContent = 'Không tìm thấy bệnh nhân';
            patientInfo.innerHTML = '<div class="text-error">Thiếu mã bệnh nhân trong đường dẫn.</div>';
            historyContainer.innerHTML = '';
            historySummary.textContent = '';
            newPredictionButton.classList.add('hidden');
            return;
        }

        try {
            await Promise.all([loadPatient(), loadHistory()]);
        } catch (error) {
            patientHeading.textContent = 'Không thể tải hồ sơ bệnh nhân';
            patientInfo.innerHTML = '<div class="text-error">Không có dữ liệu để hiển thị.</div>';
            showError(error.message);
        }
    }

    init();
});
