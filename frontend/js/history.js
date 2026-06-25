// js/history.js
document.addEventListener('DOMContentLoaded', () => {
    let currentPage = 1;
    const pageSize = 10;
    
    const tableBody = document.querySelector('#history-table tbody');
    const paginationEl = document.getElementById('pagination');
    const btnCleanup = document.getElementById('btn-cleanup');

    const labelMap = {
        'glioma_tumor': { label: 'Glioma', badge: 'badge-glioma' },
        'meningioma_tumor': { label: 'Meningioma', badge: 'badge-meningioma' },
        'pituitary_tumor': { label: 'Pituitary', badge: 'badge-pituitary' },
        'no_tumor': { label: 'Không u', badge: 'badge-notumor' }
    };

    async function loadHistory(page = 1) {
        try {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Đang tải dữ liệu...</td></tr>';
            const data = await apiFetch(`/predictions?page=${page}&page_size=${pageSize}`);
            renderTable(data.items);
            renderPagination(data.page, data.total_pages);
        } catch (error) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-error">${error.message}</td></tr>`;
        }
    }

    function renderTable(items) {
        if (!items || items.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Chưa có lịch sử chẩn đoán nào</td></tr>';
            return;
        }

        tableBody.innerHTML = items.map(p => {
            const date = new Date(p.created_at).toLocaleString('vi-VN');
            const patientCode = p.patient ? p.patient.patient_code : 'N/A';
            const doctorName = p.doctor ? p.doctor.username : 'N/A';
            const mappedClass = labelMap[p.predicted_class] || { label: p.predicted_class, badge: '' };
            const conf = `${(p.confidence * 100).toFixed(2)}%`;
            const fileStatus = p.files_deleted ? 
                '<span class="text-error" style="font-size: 0.75rem;">Đã xóa sau 24h</span>' : 
                '<span class="text-success" style="font-size: 0.75rem;">Khả dụng</span>';

            return `
                <tr>
                    <td>${date}</td>
                    <td><strong>${patientCode}</strong></td>
                    <td>${doctorName}</td>
                    <td><span class="badge ${mappedClass.badge}">${mappedClass.label}</span></td>
                    <td>${conf}</td>
                    <td>${fileStatus}</td>
                </tr>
            `;
        }).join('');
    }

    function renderPagination(page, totalPages) {
        paginationEl.innerHTML = '';
        if (totalPages <= 1) return;

        // Prev
        const prevBtn = document.createElement('button');
        prevBtn.className = 'page-item';
        prevBtn.textContent = 'Trước';
        prevBtn.disabled = page === 1;
        prevBtn.onclick = () => { currentPage = page - 1; loadHistory(currentPage); };
        paginationEl.appendChild(prevBtn);

        // Pages
        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement('button');
            btn.className = `page-item ${i === page ? 'active' : ''}`;
            btn.textContent = i;
            btn.onclick = () => { currentPage = i; loadHistory(currentPage); };
            paginationEl.appendChild(btn);
        }

        // Next
        const nextBtn = document.createElement('button');
        nextBtn.className = 'page-item';
        nextBtn.textContent = 'Sau';
        nextBtn.disabled = page === totalPages;
        nextBtn.onclick = () => { currentPage = page + 1; loadHistory(currentPage); };
        paginationEl.appendChild(nextBtn);
    }

    if (btnCleanup) {
        btnCleanup.addEventListener('click', async () => {
            if (!confirm('Bạn có chắc muốn xóa tất cả ảnh MRI và Grad-CAM đã hết hạn (>24 giờ) không?')) return;
            
            try {
                btnCleanup.disabled = true;
                btnCleanup.textContent = 'Đang xóa...';
                const res = await apiFetch('/predictions/cleanup-expired-files', { method: 'POST' });
                alert(res.message || 'Xóa file thành công');
                loadHistory(currentPage);
            } catch (error) {
                alert('Lỗi: ' + error.message);
            } finally {
                btnCleanup.disabled = false;
                btnCleanup.textContent = 'Xóa file hết hạn';
            }
        });
    }

    loadHistory();
});
