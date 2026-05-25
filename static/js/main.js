/* main.js - shared utilities */
(function () {
  // Sidebar toggle
  const toggle = document.getElementById('sbToggle');
  const sidebar = document.querySelector('.sidebar');
  if (toggle && sidebar) {
    toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
    document.addEventListener('click', e => {
      if (window.innerWidth < 992 && sidebar && !sidebar.contains(e.target) && !toggle.contains(e.target))
        sidebar.classList.remove('open');
    });
  }
  // Active link
  document.querySelectorAll('.sb-link').forEach(l => {
    if (l.href === window.location.href) l.classList.add('active');
  });
  // Auto-dismiss alerts
  setTimeout(() => {
    document.querySelectorAll('.alert.fade.show').forEach(a => a.classList.remove('show'));
  }, 4000);
})();

window.toast = function (msg, type) {
  const box = document.getElementById('toastBox');
  if (!box) return;
  const colors = { success: '#00e676', danger: '#ff2d55', warning: '#ffd60a', info: '#00d4ff' };
  const icons  = { success: 'fa-check-circle', danger: 'fa-exclamation-circle', warning: 'fa-exclamation-triangle', info: 'fa-info-circle' };
  const id = 't' + Date.now();
  box.insertAdjacentHTML('beforeend', `
    <div id="${id}" style="background:rgba(15,15,26,0.95);backdrop-filter:blur(20px);border:1px solid ${colors[type]||colors.info}30;
      color:${colors[type]||colors.info};padding:14px 20px;border-radius:14px;
      box-shadow:0 10px 40px rgba(0,0,0,0.4);display:flex;align-items:center;gap:10px;font-size:.88rem;font-weight:500;
      min-width:280px;animation:fadeInRight .3s ease;">
      <i class="fas ${icons[type]||icons.info}"></i>
      <span style="flex:1;color:#fff">${msg}</span>
      <button onclick="document.getElementById('${id}').remove()" style="background:none;border:none;color:rgba(255,255,255,0.4);cursor:pointer;font-size:1.1rem;">&times;</button>
    </div>`);
  setTimeout(() => { const el = document.getElementById(id); if (el) el.remove(); }, 5000);
};
const s = document.createElement('style');
s.textContent = '@keyframes fadeInRight{from{transform:translateX(60px);opacity:0}to{transform:translateX(0);opacity:1}}';
document.head.appendChild(s);
