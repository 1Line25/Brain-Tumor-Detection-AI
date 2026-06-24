// js/audit-logs.js
document.addEventListener('DOMContentLoaded', () => {
    const pageSize = 15;
    const tableBody = document.querySelector('#audit-table tbody');
    const paginationEl = document.getElementById('pagination');

    async function loadAuditLogs(page = 1) {
        try {
            tableBody.innerHTML =
                '<tr><td colspan="5" class="text-center">Đang tải dữ liệu...</td></tr>';
            const data = await apiFetch(
                `/audit-logs?page=${page}&page_size=${pageSize}`
            );
            renderTable(data.items);
            renderPagination(data.page, data.total_pages);
        } catch (error) {
            tableBody.textContent = '';
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 5;
            cell.className = 'text-center text-error';
            cell.textContent = error.message;
            row.appendChild(cell);
            tableBody.appendChild(row);
        }
    }

    function appendCell(row, value, className = '') {
        const cell = document.createElement('td');
        cell.textContent = value ?? '-';
        if (className) cell.className = className;
        row.appendChild(cell);
        return cell;
    }

    function renderTable(items) {
        tableBody.textContent = '';

        if (!items || items.length === 0) {
            const row = document.createElement('tr');
            const cell = document.createElement('td');
            cell.colSpan = 5;
            cell.className = 'text-center';
            cell.textContent = 'Chưa có nhật ký nào';
            row.appendChild(cell);
            tableBody.appendChild(row);
            return;
        }

        items.forEach(log => {
            const row = document.createElement('tr');
            const date = new Date(log.created_at).toLocaleString('vi-VN');
            const actorName = log.actor?.username || 'Hệ thống/không xác định';

            appendCell(row, date);
            appendCell(row, actorName);

            const actionCell = document.createElement('td');
            const badge = document.createElement('span');
            badge.className = 'badge';
            badge.style.backgroundColor = 'var(--border-color)';
            badge.style.color = 'var(--text-primary)';
            badge.textContent = log.action;
            actionCell.appendChild(badge);
            row.appendChild(actionCell);

            const entityLabel = log.entity_type
                ? `${log.entity_type}${log.entity_id ? ` (${log.entity_id})` : ''}`
                : '-';
            appendCell(row, entityLabel);
            appendCell(row, log.ip_address || '-');

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
        previousButton.addEventListener(
            'click',
            () => loadAuditLogs(page - 1)
        );
        paginationEl.appendChild(previousButton);

        for (let pageNumber = 1; pageNumber <= totalPages; pageNumber += 1) {
            const pageButton = document.createElement('button');
            pageButton.className =
                `page-item ${pageNumber === page ? 'active' : ''}`;
            pageButton.textContent = pageNumber;
            pageButton.addEventListener(
                'click',
                () => loadAuditLogs(pageNumber)
            );
            paginationEl.appendChild(pageButton);
        }

        const nextButton = document.createElement('button');
        nextButton.className = 'page-item';
        nextButton.textContent = 'Sau';
        nextButton.disabled = page === totalPages;
        nextButton.addEventListener(
            'click',
            () => loadAuditLogs(page + 1)
        );
        paginationEl.appendChild(nextButton);
    }

    loadAuditLogs();
});
