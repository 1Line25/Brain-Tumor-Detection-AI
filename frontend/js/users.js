// js/users.js
document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector('#users-table tbody');
    const paginationEl = document.getElementById('pagination');
    const pageSize = 20;
    let currentPage = 1;

    const modal = document.getElementById('user-modal');
    const btnAdd = document.getElementById('btn-add-user');
    const btnClose = document.getElementById('btn-close-modal');
    const btnCancel = document.getElementById('btn-cancel');
    const btnSave = document.getElementById('btn-save');
    const form = document.getElementById('user-form');
    const formError = document.getElementById('form-error');

    function appendCell(row, value, options = {}) {
        const cell = document.createElement('td');
        const element = options.strong
            ? document.createElement('strong')
            : document.createTextNode(String(value ?? '-'));

        if (options.strong) {
            element.textContent = String(value ?? '-');
        }

        cell.appendChild(element);
        row.appendChild(cell);
        return cell;
    }

    async function loadUsers(page = 1) {
        try {
            tableBody.innerHTML =
                '<tr><td colspan="6" class="text-center">Đang tải dữ liệu...</td></tr>';

            const data = await apiFetch(
                `/users?page=${page}&page_size=${pageSize}`
            );

            currentPage = data.page;
            renderTable(data.items);
            renderPagination(data.page, data.total_pages);
        } catch (error) {
            tableBody.textContent = '';
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 6;
            cell.className = 'text-center text-error';
            cell.textContent = error.message;
            row.appendChild(cell);
            tableBody.appendChild(row);
        }
    }

    function renderTable(users) {
        tableBody.textContent = '';

        if (!users || users.length === 0) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 6;
            cell.className = 'text-center';
            cell.textContent = 'Chưa có tài khoản nào';
            row.appendChild(cell);
            tableBody.appendChild(row);
            return;
        }

        users.forEach(user => {
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
            statusBadge.className = 'badge';
            statusBadge.style.backgroundColor = user.is_active
                ? 'rgba(16, 185, 129, 0.2)'
                : 'rgba(239, 68, 68, 0.2)';
            statusBadge.style.color = user.is_active ? '#6ee7b7' : '#fca5a5';
            statusBadge.textContent = user.is_active ? 'Hoạt động' : 'Bị khóa';
            statusCell.appendChild(statusBadge);
            row.appendChild(statusCell);

            const actionCell = document.createElement('td');
            const toggleButton = document.createElement('button');
            toggleButton.className = 'btn btn-outline btn-sm btn-toggle';
            toggleButton.dataset.id = user.id;
            toggleButton.dataset.action =
                user.is_active ? 'deactivate' : 'activate';
            toggleButton.style.padding = '0.25rem 0.5rem';
            toggleButton.style.fontSize = '0.75rem';
            toggleButton.textContent = user.is_active ? 'Khóa' : 'Mở khóa';
            toggleButton.addEventListener('click', () => {
                toggleUserStatus(
                    toggleButton.dataset.id,
                    toggleButton.dataset.action
                );
            });
            actionCell.appendChild(toggleButton);
            row.appendChild(actionCell);

            tableBody.appendChild(row);
        });
    }

    function renderPagination(page, totalPages) {
        paginationEl.textContent = '';
        if (totalPages <= 1) return;

        const previousButton = document.createElement('button');
        previousButton.className = 'page-item';
        previousButton.textContent = 'Trước';
        previousButton.disabled = page === 1;
        previousButton.addEventListener('click', () => loadUsers(page - 1));
        paginationEl.appendChild(previousButton);

        for (let pageNumber = 1; pageNumber <= totalPages; pageNumber += 1) {
            const pageButton = document.createElement('button');
            pageButton.className =
                `page-item ${pageNumber === page ? 'active' : ''}`;
            pageButton.textContent = pageNumber;
            pageButton.addEventListener(
                'click',
                () => loadUsers(pageNumber)
            );
            paginationEl.appendChild(pageButton);
        }

        const nextButton = document.createElement('button');
        nextButton.className = 'page-item';
        nextButton.textContent = 'Sau';
        nextButton.disabled = page === totalPages;
        nextButton.addEventListener('click', () => loadUsers(page + 1));
        paginationEl.appendChild(nextButton);
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

    btnSave.addEventListener('click', async event => {
        event.preventDefault();

        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const payload = {
            username: document.getElementById('username').value,
            email: document.getElementById('email').value,
            full_name: document.getElementById('full-name').value,
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
            await loadUsers(1);
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
