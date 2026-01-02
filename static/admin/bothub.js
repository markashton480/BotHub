(function () {
  function initSidebarCollapse() {
    const sidebar = document.querySelector('.unfold-sidebar') || document.querySelector('aside');
    if (!sidebar) return;

    const headings = sidebar.querySelectorAll('h2, h3, h4, .unfold-sidebar__title, .sidebar__title');
    headings.forEach((heading, index) => {
      const content = heading.nextElementSibling;
      if (!content) return;

      const titleText = heading.textContent.trim() || `Section ${index + 1}`;
      const storageKey = `bothub:nav:${titleText.toLowerCase()}`;

      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'bothub-nav-toggle';
      button.setAttribute('aria-expanded', 'true');
      button.innerHTML = `
        <span class="bothub-nav-toggle__label">${titleText}</span>
        <span class="bothub-nav-toggle__chevron" aria-hidden="true">▾</span>
      `;

      const saved = localStorage.getItem(storageKey);
      if (saved === 'collapsed') {
        content.hidden = true;
        button.classList.add('is-collapsed');
        button.setAttribute('aria-expanded', 'false');
      }

      button.addEventListener('click', () => {
        const willCollapse = !content.hidden;
        content.hidden = willCollapse;
        button.classList.toggle('is-collapsed', willCollapse);
        button.setAttribute('aria-expanded', (!willCollapse).toString());
        localStorage.setItem(storageKey, willCollapse ? 'collapsed' : 'expanded');
      });

      heading.replaceWith(button);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initSidebarCollapse();
  });
})();
