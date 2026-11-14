// Without JavaScript, the navigation links stay visible. This enhances the
// navigation with a collapsible menu on smaller screens.
(() => {
    const navigation = document.querySelector('.site-nav');
    const menuButton = document.querySelector('.nav-toggle');
    const menu = document.querySelector('#site-navigation');

    if (!navigation || !menuButton || !menu) return;

    const menuLabel = menuButton.querySelector('.nav-toggle-label');

    function setMenuOpen(open) {
        navigation.classList.toggle('is-open', open);
        menuButton.setAttribute('aria-expanded', String(open));
        menuLabel.textContent = open ? 'Закрыть' : 'Меню';
    }

    navigation.classList.add('is-enhanced');
    menuButton.hidden = false;

    menuButton.addEventListener('click', () => {
        setMenuOpen(menuButton.getAttribute('aria-expanded') !== 'true');
    });

    menu.addEventListener('click', (event) => {
        if (event.target.closest('a')) setMenuOpen(false);
    });

    document.addEventListener('click', (event) => {
        if (navigation.classList.contains('is-open') && !navigation.contains(event.target)) {
            setMenuOpen(false);
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && navigation.classList.contains('is-open')) {
            setMenuOpen(false);
            menuButton.focus();
        }
    });

    // Reset the mobile menu when switching to the desktop layout.
    const desktopLayout = window.matchMedia('(min-width: 961px)');
    desktopLayout.addEventListener('change', (event) => {
        if (event.matches) setMenuOpen(false);
    });
})();
