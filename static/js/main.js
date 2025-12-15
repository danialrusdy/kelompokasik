document.addEventListener('DOMContentLoaded', () => {
    console.log('SPK App Loaded');

    // Auto-dismiss Flash Messages
    const alerts = document.querySelectorAll('.alert-dismissible');
    if (alerts) {
        setTimeout(() => {
            alerts.forEach(alert => {
                alert.style.transition = 'opacity 0.5s ease';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            });
        }, 4000);
    }

    // Add fade-in animation to main content
    const mainContent = document.querySelector('main');
    if (mainContent) {
        mainContent.classList.add('animate-fade-in');
    }
});
