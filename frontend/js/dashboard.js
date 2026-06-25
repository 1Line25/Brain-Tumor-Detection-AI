document.addEventListener('DOMContentLoaded', () => {
    const labelMap = {
        glioma_tumor: 'Glioma',
        meningioma_tumor: 'Meningioma',
        pituitary_tumor: 'Pituitary',
        no_tumor: 'Không phát hiện u'
    };

    const colorMap = {
        glioma_tumor: '#f59e0b',
        meningioma_tumor: '#10b981',
        pituitary_tumor: '#8b5cf6',
        no_tumor: '#0ea5e9'
    };

    async function loadStatistics() {
        try {
            const stats = await apiFetch('/dashboard/statistics');

            document.getElementById('stat-patients').textContent =
                stats.total_patients.toLocaleString('vi-VN');
            document.getElementById('stat-predictions').textContent =
                stats.total_predictions.toLocaleString('vi-VN');
            document.getElementById('stat-prediction-detail').textContent =
                `${stats.successful_predictions} thành công • ${stats.failed_predictions} thất bại`;
            document.getElementById('stat-success-rate').textContent =
                `${stats.success_rate.toFixed(2)}%`;
            document.getElementById('stat-success-detail').textContent =
                `${stats.successful_predictions}/${stats.total_predictions} lần dự đoán`;
            document.getElementById('stat-review-rate').textContent =
                `${stats.review_rate.toFixed(2)}%`;
            document.getElementById('stat-review-detail').textContent =
                `${stats.reviewed_predictions}/${stats.successful_predictions} kết quả thành công`;

            renderDistribution(stats.result_distribution);
        } catch (error) {
            const errorCard = document.getElementById('dashboard-error');
            errorCard.querySelector('.card-body').textContent = error.message;
            errorCard.classList.remove('hidden');
        }
    }

    function renderDistribution(items) {
        const container = document.getElementById('result-distribution');
        container.textContent = '';

        items.forEach((item) => {
            const row = document.createElement('div');
            row.className = 'distribution-row';

            const header = document.createElement('div');
            header.className = 'distribution-row-header';
            const label = document.createElement('span');
            label.textContent = labelMap[item.tumor_class] || item.tumor_class;
            const value = document.createElement('strong');
            value.textContent = `${item.count} (${item.percentage.toFixed(2)}%)`;
            header.append(label, value);

            const track = document.createElement('div');
            track.className = 'distribution-track';
            const bar = document.createElement('div');
            bar.className = 'distribution-bar';
            bar.style.width = `${item.percentage}%`;
            bar.style.backgroundColor =
                colorMap[item.tumor_class] || 'var(--primary-color)';
            track.appendChild(bar);

            row.append(header, track);
            container.appendChild(row);
        });
    }

    loadStatistics();
});
