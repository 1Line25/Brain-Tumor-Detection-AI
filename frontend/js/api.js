// js/api.js
const API_BASE_URL = 'http://localhost:8000/api/v1';

async function apiFetch(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');
    
    const headers = {
        ...options.headers
    };
    
    // Add Authorization header if token exists and it's not a login request
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Default to JSON if Content-Type is not explicitly set or it's not FormData
    if (!(options.body instanceof FormData)) {
        if (!headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }
        if (options.body && typeof options.body === 'object') {
            options.body = JSON.stringify(options.body);
        }
    } else {
        // Remove Content-Type for FormData so browser sets the correct boundary
        delete headers['Content-Type'];
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers
        });
        
        if (response.status === 401) {
            // Unauthorized - Token expired or invalid
            localStorage.removeItem('access_token');
            localStorage.removeItem('user_role');
            localStorage.removeItem('user_fullname');
            if (!window.location.pathname.endsWith('index.html') && window.location.pathname !== '/') {
                window.location.href = 'index.html';
            }
            throw new Error('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
        }
        
        // Handle no content response
        if (response.status === 204) {
            return null;
        }

        const data = await response.json().catch(() => null);
        
        if (!response.ok) {
            throw new Error(data?.detail || data?.message || `Lỗi hệ thống (${response.status})`);
        }
        
        return data;
    } catch (error) {
        throw error;
    }
}
