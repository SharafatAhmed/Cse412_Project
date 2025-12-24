// Authentication-related JavaScript functions

document.addEventListener('DOMContentLoaded', function() {
    // Auto-focus on first form input
    const firstInput = document.querySelector('input[type="text"], input[type="email"]');
    if (firstInput) {
        firstInput.focus();
    }

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#e74c3c';
                    
                    // Create error message if not exists
                    if (!field.nextElementSibling || !field.nextElementSibling.classList.contains('field-error')) {
                        const error = document.createElement('div');
                        error.className = 'field-error';
                        error.textContent = 'This field is required';
                        error.style.color = '#e74c3c';
                        error.style.fontSize = '0.9em';
                        error.style.marginTop = '5px';
                        field.parentNode.insertBefore(error, field.nextSibling);
                    }
                } else {
                    field.style.borderColor = '#ddd';
                    const error = field.nextElementSibling;
                    if (error && error.classList.contains('field-error')) {
                        error.remove();
                    }
                }
            });

            if (!isValid) {
                e.preventDefault();
            }
        });
    });

    // Password strength checker
    const passwordInput = document.getElementById('password');
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            const strengthMeter = document.getElementById('password-strength');
            
            if (!strengthMeter) {
                const meter = document.createElement('div');
                meter.id = 'password-strength';
                meter.style.marginTop = '5px';
                meter.style.fontSize = '0.9em';
                this.parentNode.appendChild(meter);
            }
            
            const strength = checkPasswordStrength(password);
            const meter = document.getElementById('password-strength');
            meter.textContent = `Strength: ${strength.label}`;
            meter.style.color = strength.color;
        });
    }

    // Confirm password validation
    const confirmPassword = document.getElementById('confirm_password');
    if (confirmPassword) {
        confirmPassword.addEventListener('input', function() {
            const password = document.getElementById('password').value;
            const matchMessage = document.getElementById('password-match');
            
            if (!matchMessage) {
                const message = document.createElement('div');
                message.id = 'password-match';
                message.style.marginTop = '5px';
                message.style.fontSize = '0.9em';
                this.parentNode.appendChild(message);
            }
            
            const match = document.getElementById('password-match');
            if (this.value === password) {
                match.textContent = '✓ Passwords match';
                match.style.color = '#27ae60';
            } else {
                match.textContent = '✗ Passwords do not match';
                match.style.color = '#e74c3c';
            }
        });
    }

    // Auto-logout timer (2 hours)
    let idleTime = 0;
    const resetIdleTime = () => {
        idleTime = 0;
    };

    // Events that reset idle time
    ['mousemove', 'keypress', 'click', 'scroll'].forEach(event => {
        document.addEventListener(event, resetIdleTime);
    });

    // Check idle time every minute
    setInterval(() => {
        idleTime++;
        if (idleTime > 120) { // 2 hours in minutes
            // Check if user is logged in
            const userInfo = localStorage.getItem('userInfo');
            if (userInfo) {
                alert('You have been logged out due to inactivity.');
                window.location.href = '/logout';
            }
        }
    }, 60000); // Check every minute
});

// Password strength checker function
function checkPasswordStrength(password) {
    let strength = 0;
    
    // Length check
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    
    // Character variety checks
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;
    
    const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
    const colors = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60', '#16a085'];
    
    return {
        label: labels[Math.min(strength, labels.length - 1)],
        color: colors[Math.min(strength, colors.length - 1)]
    };
}

// Logout function
function logoutUser() {
    if (confirm('Are you sure you want to logout?')) {
        fetch('/logout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => {
            if (response.ok) {
                localStorage.removeItem('userInfo');
                window.location.href = '/login';
            }
        })
        .catch(error => {
            console.error('Logout error:', error);
        });
    }
}

// Check login status
function checkLoginStatus() {
    fetch('/api/check-auth')
        .then(response => response.json())
        .then(data => {
            if (data.authenticated) {
                // Update UI for logged-in user
                const loginLinks = document.querySelectorAll('a[href="/login"]');
                loginLinks.forEach(link => {
                    link.textContent = 'Profile';
                    link.href = '/profile';
                });
            }
        })
        .catch(error => console.error('Auth check failed:', error));
}

// Toggle password visibility
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const toggleBtn = document.querySelector(`#toggle-${inputId}`);
    
    if (input.type === 'password') {
        input.type = 'text';
        toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        input.type = 'password';
        toggleBtn.innerHTML = '<i class="fas fa-eye"></i>';
    }
}