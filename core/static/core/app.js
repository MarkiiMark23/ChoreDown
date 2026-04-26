// Auto-dismiss alerts after 4 seconds
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity .4s';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 400);
    }, 4000);
  });

  // Animate points display on kid dashboard
  const pointsEl = document.querySelector('.kid-points-number');
  if (pointsEl) {
    const target = parseInt(pointsEl.textContent, 10);
    let current = 0;
    const step = Math.ceil(target / 40);
    const interval = setInterval(() => {
      current = Math.min(current + step, target);
      pointsEl.textContent = current;
      if (current >= target) clearInterval(interval);
    }, 20);
  }

  // Progress bar animation
  document.querySelectorAll('.progress-fill').forEach(bar => {
    const width = bar.style.width;
    bar.style.width = '0';
    requestAnimationFrame(() => {
      bar.style.transition = 'width .6s ease';
      bar.style.width = width;
    });
  });
});
