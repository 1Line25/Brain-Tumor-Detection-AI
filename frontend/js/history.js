document.addEventListener('DOMContentLoaded', () => {
    const pageSize = 10;
    let currentPage = 1;
    let currentUser = null;
    let currentPredictionId = null;

    const tableBody = document.querySelector('#history-table tbody');
    const paginationEl = document.getElementById('pagination');
    const resultSummary = document.getElementById('history-result-summary');
    const btnCleanup = document.getElementById('btn-cleanup');
    const filterForm = document.getElementById('history-filter-form');
    const btnResetFilters = document.getElementById('btn-reset-filters');

    const detailModal = document.getElementById('history-detail-modal');
    const detailSubtitle = document.getElementById('history-detail-subtitle');
    const detailLoading = document.getElementById('history-detail-loading');
    const detailError = document.getElementById('history-detail-error');
    const detailContent = document.getElementById('history-detail-content');
    const patientInfo = document.getElementById('history-patient-info');
    const predictionInfo = document.getElementById('history-prediction-info');
    const btnCloseDetail = document.getElementById('btn-close-history-detail');
    const btnCloseDetailFooter = document.getElementById('btn-close-history-detail-footer');
    const btnSaveReview = document.getElementById('btn-save-review');
    const reviewPermissionMessage = document.getElementById('review-permission-message');
    const reviewStatusInput = document.getElementById('review-status');
    const clinicalConclusionInput = document.getElementById('clinical-conclusion');
    const doctorNotesInput = document.getElementById('doctor-notes');
    const reviewFormError = document.getElementById('review-form-error');

    const labelMap = {
        glioma_tumor: { label: 'Glioma', fullLabel: 'Glioma (U tế bào thần kinh đệm)', badge: 'badge-glioma' },
        meningioma_tumor: { label: 'Meningioma', fullLabel: 'Meningioma (U màng não)', badge: 'badge-meningioma' },
        pituitary_tumor: { label: 'Pituitary', fullLabel: 'Pituitary (U tuyến yên)', badge: 'badge-pituitary' },
        no_tumor: { label: 'Không u', fullLabel: 'Không phát hiện u', badge: 'badge-notumor' }
    };

    const reviewStatusMap = {
        pending: { label: 'Chưa đánh giá', className: 'review-pending' },
        confirmed: { label: 'Xác nhận phù hợp', className: 'review-confirmed' },
        rejected: { label: 'Không đồng ý với AI', className: 'review-rejected' }
    };

    const sexMap = {
        male: 'Nam',
        female: 'Nữ',
        other: 'Khác',
        unknown: 'Chưa cập nhật'
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

    function buildFilterQuery(page) {
        const params = new URLSearchParams({
            page: String(page),
            page_size: String(pageSize)
        });

        const patientKeyword = document.getElementById('filter-patient').value.trim();
        const doctorKeyword = document.getElementById('filter-doctor').value.trim();
        const predictedClass = document.getElementById('filter-class').value;
        const status = document.getElementById('filter-status').value;
        const reviewStatus = document.getElementById('filter-review-status').value;
        const fromDate = document.getElementById('filter-from-date').value;
        const toDate = document.getElementById('filter-to-date').value;

        if (fromDate && toDate && fromDate > toDate) {
            throw new Error('"Từ ngày" phải nhỏ hơn hoặc bằng "Đến ngày".');
        }

        if (patientKeyword) params.set('patient_keyword', patientKeyword);
        if (doctorKeyword) params.set('doctor_keyword', doctorKeyword);
        if (predictedClass) params.set('predicted_class', predictedClass);
        if (status) params.set('prediction_status', status);
        if (reviewStatus) params.set('review_status', reviewStatus);
        if (fromDate) {
            params.set('from_date', new Date(`${fromDate}T00:00:00`).toISOString());
        }
        if (toDate) {
            params.set('to_date', new Date(`${toDate}T23:59:59.999`).toISOString());
        }

        return params.toString();
    }

    async function loadCurrentUser() {
        try {
            const response = await apiFetch('/auth/me');
            currentUser = response.user;
        } catch (error) {
            currentUser = null;
        }
    }

    async function loadHistory(page = 1) {
        currentPage = page;
        try {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center">Đang tải dữ liệu...</td></tr>';
            resultSummary.textContent = 'Đang tải lịch sử...';
            const data = await apiFetch(`/predictions?${buildFilterQuery(page)}`);
            renderTable(data.items);
            renderPagination(data.page, data.total_pages);
            resultSummary.textContent = `Tìm thấy ${data.total} lần dự đoán`;
        } catch (error) {
            tableBody.innerHTML = `<tr><td colspan="7" class="text-center text-error">${escapeHtml(error.message)}</td></tr>`;
            resultSummary.textContent = 'Không thể tải lịch sử';
        }
    }

    function renderTable(items) {
        if (!items || items.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center">Không có lịch sử phù hợp với bộ lọc</td></tr>';
            return;
        }

        tableBody.innerHTML = items.map((prediction) => {
            const patient = prediction.patient || {};
            const doctor = prediction.doctor || {};
            const mappedClass = labelMap[prediction.predicted_class] || {
                label: prediction.status === 'failed' ? 'Không có kết quả' : (prediction.predicted_class || '-'),
                badge: ''
            };
            const review = reviewStatusMap[prediction.review_status] || reviewStatusMap.pending;
            const confidence = prediction.confidence == null
                ? '-'
                : `${(prediction.confidence * 100).toFixed(2)}%`;

            return `
                <tr class="history-clickable-row" tabindex="0" data-prediction-id="${escapeHtml(prediction.id)}">
                    <td>${formatDate(prediction.created_at, true)}</td>
                    <td>
                        <strong>${escapeHtml(patient.patient_code || 'N/A')}</strong>
                        <small class="table-secondary-text">${escapeHtml(patient.full_name || '')}</small>
                    </td>
                    <td>${escapeHtml(doctor.full_name || doctor.username || 'N/A')}</td>
                    <td>
                        <span class="badge ${mappedClass.badge}">${escapeHtml(mappedClass.label)}</span>
                        ${prediction.status === 'failed' ? '<small class="table-secondary-text text-error">Dự đoán thất bại</small>' : ''}
                    </td>
                    <td>${confidence}</td>
                    <td><span class="review-badge ${review.className}">${review.label}</span></td>
                    <td>
                        <button class="btn btn-outline btn-sm btn-view-prediction" data-prediction-id="${escapeHtml(prediction.id)}">
                            Xem chi tiết
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        document.querySelectorAll('.history-clickable-row').forEach((row) => {
            const open = () => openPredictionDetail(row.dataset.predictionId);
            row.addEventListener('click', (event) => {
                if (!event.target.closest('button')) open();
            });
            row.addEventListener('keydown', (event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    open();
                }
            });
        });

        document.querySelectorAll('.btn-view-prediction').forEach((button) => {
            button.addEventListener('click', () => openPredictionDetail(button.dataset.predictionId));
        });
    }

    function renderPagination(page, totalPages) {
        paginationEl.innerHTML = '';
        if (totalPages <= 1) return;

        const createButton = (label, targetPage, disabled = false, active = false) => {
            const button = document.createElement('button');
            button.className = `page-item${active ? ' active' : ''}`;
            button.textContent = label;
            button.disabled = disabled;
            button.addEventListener('click', () => loadHistory(targetPage));
            return button;
        };

        paginationEl.appendChild(createButton('Trước', page - 1, page === 1));
        for (let pageNumber = 1; pageNumber <= totalPages; pageNumber += 1) {
            paginationEl.appendChild(
                createButton(String(pageNumber), pageNumber, false, pageNumber === page)
            );
        }
        paginationEl.appendChild(createButton('Sau', page + 1, page === totalPages));
    }

    function renderPatientInfo(patient) {
        patientInfo.innerHTML = `
            <div class="patient-info-item"><span>Mã bệnh nhân</span><strong>${escapeHtml(patient.patient_code)}</strong></div>
            <div class="patient-info-item"><span>Họ và tên</span><strong>${escapeHtml(patient.full_name)}</strong></div>
            <div class="patient-info-item"><span>Ngày sinh</span><strong>${formatDate(patient.date_of_birth)}</strong></div>
            <div class="patient-info-item"><span>Giới tính</span><strong>${escapeHtml(sexMap[patient.sex] || patient.sex)}</strong></div>
            <div class="patient-info-item"><span>Số điện thoại</span><strong>${escapeHtml(patient.phone_number || '-')}</strong></div>
            <div class="patient-info-item patient-info-notes"><span>Ghi chú hồ sơ</span><strong>${escapeHtml(patient.notes || 'Không có ghi chú')}</strong></div>
        `;
    }

    function renderProbabilities(probabilities) {
        if (!probabilities) return '';
        return `
            <div class="prediction-probabilities history-probabilities">
                ${Object.entries(probabilities)
                    .sort((a, b) => b[1] - a[1])
                    .map(([key, value]) => `
                        <span>
                            <span>${escapeHtml(labelMap[key]?.fullLabel || key)}</span>
                            <strong>${(Number(value) * 100).toFixed(2)}%</strong>
                        </span>
                    `).join('')}
            </div>
        `;
    }

    function renderPredictionInfo(prediction) {
        const mappedClass = labelMap[prediction.predicted_class] || {
            fullLabel: prediction.status === 'failed' ? 'Không có kết quả' : (prediction.predicted_class || '-'),
            badge: ''
        };
        const confidence = prediction.confidence == null
            ? '-'
            : `${(prediction.confidence * 100).toFixed(2)}%`;
        const fileMessage = prediction.files_deleted
            ? '<div class="prediction-files-unavailable">Ảnh MRI và Grad-CAM đã hết thời hạn lưu trữ.</div>'
            : `
                <div class="prediction-images">
                    <figure>
                        <img src="${buildStorageUrl(prediction.mri_image_path)}" alt="Ảnh MRI gốc">
                        <figcaption>Ảnh MRI gốc</figcaption>
                    </figure>
                    <figure>
                        ${prediction.gradcam_image_path
                            ? `<img src="${buildStorageUrl(prediction.gradcam_image_path)}" alt="Ảnh Grad-CAM">`
                            : '<div class="image-placeholder">Không có ảnh Grad-CAM</div>'}
                        <figcaption>Vùng chú ý Grad-CAM</figcaption>
                    </figure>
                </div>
            `;

        predictionInfo.innerHTML = `
            <div class="history-prediction-summary">
                <div><span>Thời gian</span><strong>${formatDate(prediction.created_at, true)}</strong></div>
                <div><span>Bác sĩ thực hiện</span><strong>${escapeHtml(prediction.doctor.full_name || prediction.doctor.username)}</strong></div>
                <div><span>Trạng thái</span><strong>${prediction.status === 'success' ? 'Thành công' : 'Thất bại'}</strong></div>
                <div><span>Kết quả AI</span><strong class="badge ${mappedClass.badge}">${escapeHtml(mappedClass.fullLabel)}</strong></div>
                <div><span>Độ tin cậy</span><strong>${confidence}</strong></div>
                <div><span>Ảnh hết hạn</span><strong>${formatDate(prediction.expires_at, true)}</strong></div>
            </div>
            ${prediction.status === 'success' ? fileMessage : `
                <div class="prediction-files-unavailable text-error">
                    Lần dự đoán này thất bại và không có kết quả để đánh giá.
                </div>
            `}
            ${prediction.status === 'success' ? renderProbabilities(prediction.probabilities) : ''}
        `;
    }

    function configureReviewForm(prediction) {
        const canReview = (
            currentUser
            && currentUser.id === prediction.doctor_id
            && prediction.status === 'success'
        );

        reviewStatusInput.value = prediction.review_status || 'pending';
        clinicalConclusionInput.value = prediction.clinical_conclusion || '';
        doctorNotesInput.value = prediction.doctor_notes || '';

        [reviewStatusInput, clinicalConclusionInput, doctorNotesInput].forEach((field) => {
            field.disabled = !canReview;
        });
        btnSaveReview.classList.toggle('hidden', !canReview);

        if (canReview) {
            reviewPermissionMessage.textContent = prediction.reviewed_at
                ? `Cập nhật gần nhất: ${formatDate(prediction.reviewed_at, true)}`
                : 'Bạn có thể cập nhật đánh giá cho kết quả này.';
        } else if (prediction.status === 'failed') {
            reviewPermissionMessage.textContent = 'Không thể đánh giá một lần dự đoán thất bại.';
        } else {
            reviewPermissionMessage.textContent = 'Chỉ người thực hiện dự đoán mới có thể sửa đánh giá.';
        }
    }

    async function openPredictionDetail(predictionId) {
        currentPredictionId = predictionId;
        detailModal.classList.remove('hidden');
        detailLoading.classList.remove('hidden');
        detailError.classList.add('hidden');
        detailContent.classList.add('hidden');
        reviewFormError.classList.add('hidden');
        btnSaveReview.classList.add('hidden');
        detailSubtitle.textContent = 'Đang tải...';

        try {
            const prediction = await apiFetch(`/predictions/${predictionId}`);
            const patient = await apiFetch(`/patients/${prediction.patient_id}`);
            detailSubtitle.textContent = `${patient.patient_code} - ${patient.full_name}`;
            renderPatientInfo(patient);
            renderPredictionInfo(prediction);
            configureReviewForm(prediction);
            detailContent.classList.remove('hidden');
        } catch (error) {
            detailError.textContent = error.message;
            detailError.classList.remove('hidden');
        } finally {
            detailLoading.classList.add('hidden');
        }
    }

    function closePredictionDetail() {
        detailModal.classList.add('hidden');
        currentPredictionId = null;
    }

    async function saveReview() {
        if (!currentPredictionId) return;

        try {
            btnSaveReview.disabled = true;
            btnSaveReview.textContent = 'Đang lưu...';
            reviewFormError.classList.add('hidden');

            const updated = await apiFetch(`/predictions/${currentPredictionId}/review`, {
                method: 'PATCH',
                body: {
                    review_status: reviewStatusInput.value,
                    clinical_conclusion: clinicalConclusionInput.value || null,
                    doctor_notes: doctorNotesInput.value || null
                }
            });

            configureReviewForm(updated);
            await loadHistory(currentPage);
        } catch (error) {
            reviewFormError.textContent = error.message;
            reviewFormError.classList.remove('hidden');
        } finally {
            btnSaveReview.disabled = false;
            btnSaveReview.textContent = 'Lưu đánh giá';
        }
    }

    filterForm.addEventListener('submit', (event) => {
        event.preventDefault();
        loadHistory(1);
    });

    btnResetFilters.addEventListener('click', () => {
        filterForm.reset();
        loadHistory(1);
    });

    btnCloseDetail.addEventListener('click', closePredictionDetail);
    btnCloseDetailFooter.addEventListener('click', closePredictionDetail);
    btnSaveReview.addEventListener('click', saveReview);
    detailModal.addEventListener('click', (event) => {
        if (event.target === detailModal) closePredictionDetail();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !detailModal.classList.contains('hidden')) {
            closePredictionDetail();
        }
    });

    if (btnCleanup) {
        btnCleanup.addEventListener('click', async () => {
            if (!confirm('Bạn có chắc muốn xóa tất cả ảnh MRI và Grad-CAM đã hết hạn (>24 giờ) không?')) return;

            try {
                btnCleanup.disabled = true;
                btnCleanup.textContent = 'Đang xóa...';
                const response = await apiFetch('/predictions/cleanup-expired-files', { method: 'POST' });
                alert(response.message || 'Xóa file thành công');
                loadHistory(currentPage);
            } catch (error) {
                alert(`Lỗi: ${error.message}`);
            } finally {
                btnCleanup.disabled = false;
                btnCleanup.textContent = 'Xóa file hết hạn';
            }
        });
    }

    async function init() {
        await loadCurrentUser();
        await loadHistory();
    }

    init();
});
