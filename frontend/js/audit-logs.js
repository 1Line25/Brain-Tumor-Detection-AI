// js/audit-logs.js
document.addEventListener('DOMContentLoaded', () => {
    let currentPage = 1;
    const pageSize = 15;
    
    const tableBody = document.querySelector('#audit-table tbody');
    const paginationEl = document.getElementById('pagination');

    async function loadAuditLogs(page = 1) {
        try {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Đang tải dữ liệu...</td></tr>';
            const data = await apiFetch(`/audit-logs?page=${page}&page_size=${pageSize}`);
            renderTable(data.items);
            renderPagination(data.page, data.pages);
        } catch (error) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-error">${error.message}</td></tr>`;
        }
    }

    function renderTable(items) {
        if (!items || items.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center">Chưa có nhật ký nào</td></tr>';
            return;
        }

        tableBody.innerHTML = items.map(log => {
            const date = new Date(log.created_at).toLocaleString('vi-VN');
            const actorName = log.actor ? log.actor.username : 'Hệ thống';
            
            return `
                <tr>
                    <td style="font-size: 0.8rem; color: var(--text-secondary);">${date}</td>
                    <td><strong>${actorName}</strong></td>
                    <td><span class="badge" style="background-color: var(--border-color); color: var(--text-primary);">${log.action}</span></td>
                    <td>${log.entity_type} <span style="color: var(--text-secondary); font-size: 0.75rem;">(${log.entity_id})</span></td>
                    <td style="font-size: 0.8rem;">${log.ip_address || '-'}</td>
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
        prevBtn.onclick = () => { currentPage = page - 1; loadAuditLogs(currentPage); };
        paginationEl.appendChild(prevBtn);

        // Pages
        for (let i = 1; i <= totalPages; i++) {
            const btn = document.createElement('button');
            btn.className = `page-item ${i === page ? 'active' : ''}`;
            btn.textContent = i;
            btn.onclick = () => { currentPage = i; loadAuditLogs(currentPage); };
            paginationEl.appendChild(btn);
        }

        // Next
        const nextBtn = document.createElement('button');
        nextBtn.className = 'page-item';
        nextBtn.textContent = 'Sau';
        nextBtn.disabled = page === totalPages;
        nextBtn.onclick = () => { currentPage = page + 1; loadAuditLogs(currentPage); };
        paginationEl.appendChild(nextBtn);
    }

    loadAuditLogs();
});
