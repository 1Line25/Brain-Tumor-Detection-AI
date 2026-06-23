// js/users.js
document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector('#users-table tbody');
    
    // Modal elements
    const modal = document.getElementById('user-modal');
    const btnAdd = document.getElementById('btn-add-user');
    const btnClose = document.getElementById('btn-close-modal');
    const btnCancel = document.getElementById('btn-cancel');
    const btnSave = document.getElementById('btn-save');
    const form = document.getElementById('user-form');
    const formError = document.getElementById('form-error');

    async function loadUsers() {
        try {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Đang tải dữ liệu...</td></tr>';
            const users = await apiFetch('/users');
            renderTable(users);
        } catch (error) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-error">${error.message}</td></tr>`;
        }
    }

    function renderTable(users) {
        if (!users || users.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Chưa có người dùng nào</td></tr>';
            return;
        }

        tableBody.innerHTML = users.map(u => {
            const roleBadge = u.role === 'admin' ? 'badge-admin' : 'badge-doctor';
            const statusBadge = u.is_active ? 
                '<span class="badge" style="background-color: rgba(16, 185, 129, 0.2); color: #6ee7b7;">Hoạt động</span>' : 
                '<span class="badge" style="background-color: rgba(239, 68, 68, 0.2); color: #fca5a5;">Bị khóa</span>';
            
            const toggleAction = u.is_active ? 
                `<button class="btn btn-outline btn-sm btn-toggle" data-id="${u.id}" data-action="deactivate" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">Khóa</button>` :
                `<button class="btn btn-outline btn-sm btn-toggle" data-id="${u.id}" data-action="activate" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">Mở khóa</button>`;

            return `
                <tr>
                    <td><strong>${u.username}</strong></td>
                    <td>${u.email}</td>
                    <td><span class="badge ${roleBadge}">${u.role.toUpperCase()}</span></td>
                    <td>${statusBadge}</td>
                    <td>${toggleAction}</td>
                </tr>
            `;
        }).join('');

        // Attach events
        document.querySelectorAll('.btn-toggle').forEach(btn => {
            btn.addEventListener('click', () => toggleUserStatus(btn.dataset.id, btn.dataset.action));
        });
    }

    async function toggleUserStatus(id, action) {
        if (!confirm(`Bạn có chắc muốn ${action === 'activate' ? 'Mở khóa' : 'Khóa'} tài khoản này?`)) return;
        
        try {
            await apiFetch(`/users/${id}/${action}`, { method: 'POST' });
            loadUsers();
        } catch (error) {
            alert('Lỗi: ' + error.message);
        }
    }

    // Modal Operations
    function openModal() {
        modal.classList.remove('hidden');
        formError.classList.add('hidden');
    }

    function closeModal() {
        modal.classList.add('hidden');
        form.reset();
    }

    btnAdd.addEventListener('click', openModal);
    btnClose.addEventListener('click', closeModal);
    btnCancel.addEventListener('click', closeModal);

    btnSave.addEventListener('click', async (e) => {
        e.preventDefault();
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const payload = {
            username: document.getElementById('username').value,
            email: document.getElementById('email').value,
            password: document.getElementById('password').value,
            role: document.getElementById('role').value
        };

        try {
            btnSave.disabled = true;
            btnSave.textContent = 'Đang lưu...';
            
            await apiFetch('/users', {
                method: 'POST',
                body: payload
            });
            
            closeModal();
            loadUsers();
        } catch (error) {
            formError.textContent = error.message;
            formError.classList.remove('hidden');
        } finally {
            btnSave.disabled = false;
            btnSave.textContent = 'Tạo tài khoản';
        }
    });

    loadUsers();
});
