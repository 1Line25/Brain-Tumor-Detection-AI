document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector('#users-table tbody');
    const paginationEl = document.getElementById('pagination');
    const pageSize = 20;
    let currentPage = 1;

    const modal = document.getElementById('user-modal');
    const modalTitle = document.getElementById('user-modal-title');
    const btnAdd = document.getElementById('btn-add-user');
    const btnClose = document.getElementById('btn-close-modal');
    const btnCancel = document.getElementById('btn-cancel');
    const btnSave = document.getElementById('btn-save');
    const form = document.getElementById('user-form');
    const formError = document.getElementById('form-error');
    const passwordGroup = document.getElementById('password-group');
    const passwordInput = document.getElementById('password');

    const passwordModal = document.getElementById('password-reset-modal');
    const passwordResetUser = document.getElementById('password-reset-user');
    const passwordResetForm = document.getElementById('password-reset-form');
    const passwordResetError = document.getElementById('password-reset-error');
    const btnClosePasswordModal = document.getElementById('btn-close-password-modal');
    const btnCancelPasswordReset = document.getElementById('btn-cancel-password-reset');
    const btnSavePassword = document.getElementById('btn-save-password');

    function appendCell(row, value, options = {}) {
        const cell = document.createElement('td');
        const element = options.strong
            ? document.createElement('strong')
            : document.createTextNode(String(value ?? '-'));
        if (options.strong) element.textContent = String(value ?? '-');
        cell.appendChild(element);
        row.appendChild(cell);
        return cell;
    }

    async function loadUsers(page = 1) {
        try {
            tableBody.innerHTML =
                '<tr><td colspan="6" class="text-center">Đang tải dữ liệu...</td></tr>';
            const data = await apiFetch(`/users?page=${page}&page_size=${pageSize}`);
            currentPage = data.page;
            renderTable(data.items);
            renderPagination(data.page, data.total_pages);
        } catch (error) {
            tableBody.innerHTML =
                `<tr><td colspan="6" class="text-center text-error">${error.message}</td></tr>`;
        }
    }

    function renderTable(users) {
        tableBody.textContent = '';
        if (!users || users.length === 0) {
            tableBody.innerHTML =
                '<tr><td colspan="6" class="text-center">Chưa có tài khoản nào</td></tr>';
            return;
        }

        users.forEach((user) => {
            const row = document.createElement('tr');
            appendCell(row, user.username, { strong: true });
            appendCell(row, user.full_name);
            appendCell(row, user.email);

            const roleCell = document.createElement('td');
            const roleBadge = document.createElement('span');
            roleBadge.className =
                `badge ${user.role === 'admin' ? 'badge-admin' : 'badge-doctor'}`;
            roleBadge.textContent = user.role.toUpperCase();
            roleCell.appendChild(roleBadge);
            row.appendChild(roleCell);

            const statusCell = document.createElement('td');
            const statusBadge = document.createElement('span');
            statusBadge.className = `badge ${user.is_active ? 'status-active' : 'status-inactive'}`;
            statusBadge.textContent = user.is_active ? 'Hoạt động' : 'Bị khóa';
            statusCell.appendChild(statusBadge);
            row.appendChild(statusCell);

            const actionCell = document.createElement('td');
            actionCell.className = 'user-actions';

            const editButton = createActionButton('Sửa', () => openEditModal(user.id));
            const resetButton = createActionButton(
                'Đặt lại mật khẩu',
                () => openPasswordResetModal(user)
            );
            const toggleButton = createActionButton(
                user.is_active ? 'Khóa' : 'Mở khóa',
                () => toggleUserStatus(
                    user.id,
                    user.is_active ? 'deactivate' : 'activate'
                )
            );
            actionCell.append(editButton, resetButton, toggleButton);
            row.appendChild(actionCell);
            tableBody.appendChild(row);
        });
    }

    function createActionButton(label, handler) {
        const button = document.createElement('button');
        button.className = 'btn btn-outline btn-sm';
        button.type = 'button';
        button.textContent = label;
        button.addEventListener('click', handler);
        return button;
    }

    function renderPagination(page, totalPages) {
        paginationEl.textContent = '';
        if (totalPages <= 1) return;

        const createPageButton = (label, targetPage, disabled = false, active = false) => {
            const button = document.createElement('button');
            button.className = `page-item${active ? ' active' : ''}`;
            button.textContent = label;
            button.disabled = disabled;
            button.addEventListener('click', () => loadUsers(targetPage));
            return button;
        };

        paginationEl.appendChild(createPageButton('Trước', page - 1, page === 1));
        for (let number = 1; number <= totalPages; number += 1) {
            paginationEl.appendChild(
                createPageButton(String(number), number, false, number === page)
            );
        }
        paginationEl.appendChild(
            createPageButton('Sau', page + 1, page === totalPages)
        );
    }

    async function toggleUserStatus(id, action) {
        const actionLabel = action === 'activate' ? 'mở khóa' : 'khóa';
        if (!confirm(`Bạn có chắc muốn ${actionLabel} tài khoản này?`)) return;
        try {
            await apiFetch(`/users/${id}/${action}`, { method: 'POST' });
            await loadUsers(currentPage);
        } catch (error) {
            alert(`Lỗi: ${error.message}`);
        }
    }

    function openCreateModal() {
        form.reset();
        document.getElementById('user-id').value = '';
        document.getElementById('username').disabled = false;
        passwordGroup.classList.remove('hidden');
        passwordInput.required = true;
        modalTitle.textContent = 'Tạo Tài khoản mới';
        btnSave.textContent = 'Tạo tài khoản';
        formError.classList.add('hidden');
        modal.classList.remove('hidden');
    }

    async function openEditModal(userId) {
        try {
            const user = await apiFetch(`/users/${userId}`);
            form.reset();
            document.getElementById('user-id').value = user.id;
            document.getElementById('username').value = user.username;
            document.getElementById('username').disabled = true;
            document.getElementById('email').value = user.email;
            document.getElementById('full-name').value = user.full_name;
            document.getElementById('role').value = user.role;
            passwordGroup.classList.add('hidden');
            passwordInput.required = false;
            modalTitle.textContent = 'Cập nhật Tài khoản';
            btnSave.textContent = 'Lưu thay đổi';
            formError.classList.add('hidden');
            modal.classList.remove('hidden');
        } catch (error) {
            alert(`Không thể tải tài khoản: ${error.message}`);
        }
    }

    function closeModal() {
        modal.classList.add('hidden');
        form.reset();
    }

    function openPasswordResetModal(user) {
        passwordResetForm.reset();
        passwordResetError.classList.add('hidden');
        document.getElementById('password-reset-user-id').value = user.id;
        passwordResetUser.textContent = `${user.username} - ${user.full_name}`;
        passwordModal.classList.remove('hidden');
    }

    function closePasswordResetModal() {
        passwordModal.classList.add('hidden');
        passwordResetForm.reset();
    }

    btnAdd.addEventListener('click', openCreateModal);
    btnClose.addEventListener('click', closeModal);
    btnCancel.addEventListener('click', closeModal);
    btnClosePasswordModal.addEventListener('click', closePasswordResetModal);
    btnCancelPasswordReset.addEventListener('click', closePasswordResetModal);

    btnSave.addEventListener('click', async (event) => {
        event.preventDefault();
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const userId = document.getElementById('user-id').value;
        const payload = {
            email: document.getElementById('email').value,
            full_name: document.getElementById('full-name').value,
            role: document.getElementById('role').value
        };

        if (!userId) {
            payload.username = document.getElementById('username').value;
            payload.password = passwordInput.value;
        }

        try {
            btnSave.disabled = true;
            btnSave.textContent = 'Đang lưu...';
            await apiFetch(userId ? `/users/${userId}` : '/users', {
                method: userId ? 'PATCH' : 'POST',
                body: payload
            });
            closeModal();
            await loadUsers(userId ? currentPage : 1);
        } catch (error) {
            formError.textContent = error.message;
            formError.classList.remove('hidden');
        } finally {
            btnSave.disabled = false;
            btnSave.textContent = userId ? 'Lưu thay đổi' : 'Tạo tài khoản';
        }
    });

    btnSavePassword.addEventListener('click', async (event) => {
        event.preventDefault();
        if (!passwordResetForm.checkValidity()) {
            passwordResetForm.reportValidity();
            return;
        }

        const password = document.getElementById('new-password').value;
        const confirmation = document.getElementById('confirm-password').value;
        if (password !== confirmation) {
            passwordResetError.textContent = 'Hai mật khẩu chưa khớp.';
            passwordResetError.classList.remove('hidden');
            return;
        }

        try {
            btnSavePassword.disabled = true;
            btnSavePassword.textContent = 'Đang lưu...';
            const userId = document.getElementById('password-reset-user-id').value;
            await apiFetch(`/users/${userId}/reset-password`, {
                method: 'POST',
                body: { new_password: password }
            });
            closePasswordResetModal();
            alert('Đặt lại mật khẩu thành công.');
        } catch (error) {
            passwordResetError.textContent = error.message;
            passwordResetError.classList.remove('hidden');
        } finally {
            btnSavePassword.disabled = false;
            btnSavePassword.textContent = 'Đặt lại mật khẩu';
        }
    });

    loadUsers();
});
