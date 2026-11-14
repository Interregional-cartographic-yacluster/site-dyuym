// The native dropdowns work without JavaScript. The mobile toggle and these
// enhancements are enabled only after their event handlers are ready.
(() => {
    const navigation = document.querySelector('.site-nav');
    if (!navigation) return;

    const dropdowns = [...navigation.querySelectorAll('.nav-dropdown')];
    const toggle = navigation.querySelector('.nav-toggle');
    const menu = navigation.querySelector('.nav-list');
    const brand = navigation.querySelector('.nav-brand');

    function closeDropdowns(except = null) {
        dropdowns.forEach((dropdown) => {
            if (dropdown !== except) dropdown.open = false;
        });
    }

    function setMenuOpen(open) {
        if (!toggle) return;
        navigation.classList.toggle('is-open', open);
        toggle.setAttribute('aria-expanded', String(open));
        toggle.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    }

    dropdowns.forEach((dropdown) => {
        dropdown.addEventListener('toggle', () => {
            if (dropdown.open) closeDropdowns(dropdown);
        });
    });

    if (toggle && menu) {
        toggle.addEventListener('click', () => {
            const opening = !navigation.classList.contains('is-open');
            if (!opening) closeDropdowns();
            setMenuOpen(opening);
        });

        // Preserve focus when a responsive layout change hides the focused item.
        const mobileLayout = window.matchMedia && window.matchMedia('(max-width: 720px)');
        const handleLayoutChange = (event) => {
            const focused = document.activeElement;
            const focusWasInMenu = menu.contains(focused);
            const focusWasOnToggle = focused === toggle;
            const focusedPanel = focused.closest('.nav-dropdown-panel');
            const focusedDropdown = focused.closest('.nav-dropdown');
            closeDropdowns();
            setMenuOpen(false);
            if (event.matches && focusWasInMenu) {
                toggle.focus();
            } else if (!event.matches && focusWasOnToggle && brand) {
                brand.focus();
            } else if (!event.matches && focusedPanel && focusedDropdown) {
                focusedDropdown.querySelector('summary').focus();
            }
        };
        if (mobileLayout && mobileLayout.addEventListener) {
            mobileLayout.addEventListener('change', handleLayoutChange);
        } else if (mobileLayout && mobileLayout.addListener) {
            mobileLayout.addListener(handleLayoutChange);
        }

        navigation.classList.add('nav-ready');
    }

    navigation.addEventListener('click', (event) => {
        if (event.target.closest('a')) {
            closeDropdowns();
            setMenuOpen(false);
        }
    });

    document.addEventListener('click', (event) => {
        if (!navigation.contains(event.target)) {
            closeDropdowns();
            setMenuOpen(false);
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') return;

        const openSubmenu = document.activeElement.closest('.nav-submenu[open]');
        if (openSubmenu && navigation.contains(openSubmenu)) {
            openSubmenu.open = false;
            openSubmenu.querySelector('summary').focus();
            return;
        }

        const openDropdown = dropdowns.find((dropdown) => dropdown.open);
        if (openDropdown) {
            closeDropdowns();
            openDropdown.querySelector('summary').focus();
            return;
        }

        if (toggle && navigation.classList.contains('is-open')) {
            setMenuOpen(false);
            toggle.focus();
        }
    });
})();
