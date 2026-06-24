// js/auth.js
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is logged in
    const token = localStorage.getItem('access_token');
    const currentPage = window.location.pathname.split('/').pop();

    if (token && (currentPage === 'index.html' || currentPage === '')) {
        // Already logged in, redirect to dashboard
        window.location.href = 'dashboard.html';
    } else if (!token && currentPage !== 'index.html' && currentPage !== '') {
        // Not logged in, redirect to login
        window.location.href = 'index.html';
    }

    // Set user info on authenticated pages
    if (token && currentPage !== 'index.html' && currentPage !== '') {
        const fullname = localStorage.getItem('user_fullname') || 'User';
        const role = localStorage.getItem('user_role') || 'doctor';
        const adminPages = new Set(['users.html', 'audit-logs.html']);

        if (role !== 'admin' && adminPages.has(currentPage)) {
            window.location.replace('dashboard.html');
            return;
        }
        
        const userInfoEl = document.getElementById('user-fullname');
        const userRoleEl = document.getElementById('user-role');
        
        if (userInfoEl) userInfoEl.textContent = fullname;
        if (userRoleEl) {
            userRoleEl.textContent = role;
            userRoleEl.classList.add(`badge-${role}`);
        }

        // Hide admin links for doctors
        if (role !== 'admin') {
            document.querySelectorAll('.admin-only').forEach(el => el.classList.add('hidden'));
        } else {
            document.querySelectorAll('.admin-only').forEach(
                el => el.classList.remove('hidden')
            );
        }
    }

    // Handle logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                await apiFetch('/auth/logout', { method: 'POST' });
            } catch (error) {
                // Token có thể đã hết hạn; vẫn phải xóa phiên cục bộ.
            } finally {
                localStorage.removeItem('access_token');
                localStorage.removeItem('user_role');
                localStorage.removeItem('user_fullname');
                window.location.href = 'index.html';
            }
        });
    }

    // Handle login form submission
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const identifier = document.getElementById('identifier').value;
            const password = document.getElementById('password').value;
            const errorMsg = document.getElementById('login-error');
            const submitBtn = document.getElementById('login-btn');
            
            errorMsg.classList.add('hidden');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Đang đăng nhập...';
            
            try {
                const response = await apiFetch('/auth/login', {
                    method: 'POST',
                    body: { identifier, password }
                });
                
                // Save auth data
                localStorage.setItem('access_token', response.access_token);
                localStorage.setItem('user_role', response.user.role);
                localStorage.setItem('user_fullname', response.user.username); // Fallback to username for now
                
                // Redirect
                window.location.href = 'dashboard.html';
            } catch (error) {
                errorMsg.textContent = error.message;
                errorMsg.classList.remove('hidden');
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Đăng nhập';
            }
        });
    }
});
