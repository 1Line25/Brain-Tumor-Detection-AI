// js/patients.js
document.addEventListener('DOMContentLoaded', () => {
    let currentPage = 1;
    const pageSize = 10;
    let currentKeyword = '';

    const tableBody = document.querySelector('#patients-table tbody');
    const paginationEl = document.getElementById('pagination');
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('btn-search');
    
    // Modal elements
    const modal = document.getElementById('patient-modal');
    const btnAdd = document.getElementById('btn-add-patient');
    const btnClose = document.getElementById('btn-close-modal');
    const btnCancel = document.getElementById('btn-cancel');
    const btnSave = document.getElementById('btn-save');
    const form = document.getElementById('patient-form');
    const modalTitle = document.getElementById('modal-title');
    const formError = document.getElementById('form-error');
    const duplicateWarning = document.getElementById('duplicate-warning');

    // Load Data
    async function loadPatients(page = 1, keyword = '') {
        try {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Đang tải dữ liệu...</td></tr>';
            
            let url = `/patients?page=${page}&page_size=${pageSize}`;
            if (keyword) {
                url += `&keyword=${encodeURIComponent(keyword)}`;
            }
            
            const data = await apiFetch(url);
            renderTable(data.items);
            renderPagination(data.page, data.total_pages);
        } catch (error) {
            tableBody.innerHTML = `<tr><td colspan="6" class="text-center text-error">${error.message}</td></tr>`;
        }
    }

    function renderTable(items) {
        if (!items || items.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center">Không tìm thấy dữ liệu</td></tr>';
            return;
        }

        const sexMap = { 'male': 'Nam', 'female': 'Nữ', 'other': 'Khác' };

        tableBody.innerHTML = items.map(p => `
            <tr>
                <td>${p.patient_code}</td>
                <td><strong>${p.full_name}</strong></td>
                <td>${p.date_of_birth || '-'}</td>
                <td>${sexMap[p.sex] || p.sex}</td>
                <td>${p.phone_number || '-'}</td>
                <td>
                    <div class="patient-actions">
                        <a href="patient-detail.html?patient_id=${p.id}" class="btn btn-outline btn-sm">Xem chi tiết</a>
                        <button class="btn btn-outline btn-sm btn-edit" data-id="${p.id}">Sửa</button>
                        <a href="prediction.html?patient_id=${p.id}" class="btn btn-primary btn-sm">Chẩn đoán MRI</a>
                    </div>
                </td>
            </tr>
        `).join('');

        // Attach edit events
        document.querySelectorAll('.btn-edit').forEach(btn => {
            btn.addEventListener('click', () => openEditModal(btn.dataset.id));
        });
    }

    function renderPagination(page, totalPages) {
        paginationEl.innerHTML = '';
        if (totalPages <= 1) return;

        // Prev
        const prevBtn = document.createElement('button');
        prevBtn.className = 'page-item';
        prevBtn.textContent = 'Trước';
        prevBtn.disabled = page === 1;
        prevBtn.onclick = () => { currentPage = page - 1; loadPatients(currentPage, currentKeyword); };
        paginationEl.appendChild(prevBtn);

        // Pages
        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement('button');
            btn.className = `page-item ${i === page ? 'active' : ''}`;
            btn.textContent = i;
            btn.onclick = () => { currentPage = i; loadPatients(currentPage, currentKeyword); };
            paginationEl.appendChild(btn);
        }

        // Next
        const nextBtn = document.createElement('button');
        nextBtn.className = 'page-item';
        nextBtn.textContent = 'Sau';
        nextBtn.disabled = page === totalPages;
        nextBtn.onclick = () => { currentPage = page + 1; loadPatients(currentPage, currentKeyword); };
        paginationEl.appendChild(nextBtn);
    }

    // Search
    searchBtn.addEventListener('click', () => {
        currentKeyword = searchInput.value.trim();
        currentPage = 1;
        loadPatients(currentPage, currentKeyword);
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchBtn.click();
        }
    });

    // Modal Operations
    function openModal() {
        modal.classList.remove('hidden');
        formError.classList.add('hidden');
        duplicateWarning.classList.add('hidden');
    }

    function closeModal() {
        modal.classList.add('hidden');
        form.reset();
        document.getElementById('patient-id').value = '';
        duplicateWarning.textContent = '';
    }

    btnAdd.addEventListener('click', () => {
        modalTitle.textContent = 'Thêm Bệnh nhân';
        openModal();
    });

    btnClose.addEventListener('click', closeModal);
    btnCancel.addEventListener('click', closeModal);

    function normalizePhone(value) {
        const compact = value.trim().replace(/[\s().-]/g, '');
        return compact.startsWith('+84')
            ? `0${compact.slice(3)}`
            : compact;
    }

    function validatePhone(value) {
        if (!value) return true;
        return value.startsWith('+')
            ? /^\+[1-9]\d{8,14}$/.test(value)
            : /^0\d{9,10}$/.test(value);
    }

    async function confirmPossibleDuplicates(payload, patientId) {
        const result = await apiFetch('/patients/duplicate-check', {
            method: 'POST',
            body: {
                full_name: payload.full_name,
                date_of_birth: payload.date_of_birth,
                phone_number: payload.phone_number,
                exclude_patient_id: patientId || null
            }
        });

        const duplicates = result.possible_duplicates || [];
        if (!duplicates.length) {
            duplicateWarning.classList.add('hidden');
            return true;
        }

        duplicateWarning.textContent = '';
        const title = document.createElement('strong');
        title.textContent = 'Phát hiện hồ sơ có khả năng bị trùng:';
        const list = document.createElement('ul');
        duplicates.forEach((patient) => {
            const item = document.createElement('li');
            item.textContent = `${patient.patient_code} - ${patient.full_name} - ${patient.date_of_birth || 'Chưa có ngày sinh'} - ${patient.phone_number || 'Chưa có SĐT'}`;
            list.appendChild(item);
        });
        duplicateWarning.append(title, list);
        duplicateWarning.classList.remove('hidden');

        return confirm(
            `Có ${duplicates.length} hồ sơ tương tự. Bạn vẫn muốn tiếp tục lưu hồ sơ này?`
        );
    }

    async function openEditModal(id) {
        try {
            const patient = await apiFetch(`/patients/${id}`);
            document.getElementById('patient-id').value = patient.id;
            
            document.getElementById('full-name').value = patient.full_name;
            document.getElementById('dob').value = patient.date_of_birth || '';
            document.getElementById('sex').value = patient.sex;
            document.getElementById('phone').value = patient.phone_number || '';
            document.getElementById('notes').value = patient.notes || '';
            
            modalTitle.textContent = 'Cập nhật Bệnh nhân';
            openModal();
        } catch (error) {
            alert('Lỗi tải thông tin: ' + error.message);
        }
    }

    btnSave.addEventListener('click', async (e) => {
        e.preventDefault();
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const id = document.getElementById('patient-id').value;
        const normalizedPhone = normalizePhone(
            document.getElementById('phone').value
        );

        if (!validatePhone(normalizedPhone)) {
            formError.textContent = 'Số điện thoại không hợp lệ. Số trong nước phải bắt đầu bằng 0 và có 10–11 chữ số; số quốc tế bắt đầu bằng +.';
            formError.classList.remove('hidden');
            return;
        }

        const payload = {
            full_name: document.getElementById('full-name').value,
            date_of_birth: document.getElementById('dob').value || null,
            sex: document.getElementById('sex').value,
            phone_number: normalizedPhone || null,
            notes: document.getElementById('notes').value || null
        };

        try {
            btnSave.disabled = true;
            btnSave.textContent = 'Đang kiểm tra...';

            const shouldContinue = await confirmPossibleDuplicates(payload, id);
            if (!shouldContinue) return;

            btnSave.textContent = 'Đang lưu...';
            
            if (id) {
                // Update
                await apiFetch(`/patients/${id}`, {
                    method: 'PATCH',
                    body: payload
                });
            } else {
                // Create
                await apiFetch('/patients', {
                    method: 'POST',
                    body: payload
                });
            }
            
            closeModal();
            loadPatients(currentPage, currentKeyword);
        } catch (error) {
            formError.textContent = error.message;
            formError.classList.remove('hidden');
        } finally {
            btnSave.disabled = false;
            btnSave.textContent = 'Lưu lại';
        }
    });

    // Init
    loadPatients();
});
