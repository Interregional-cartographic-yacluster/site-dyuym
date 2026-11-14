// The native details elements work without JavaScript. These enhancements
// close the other section, close on outside click, and support Escape.
(() => {
    const navigation = document.querySelector('.site-nav');
    if (!navigation) return;

    const dropdowns = [...navigation.querySelectorAll('.nav-dropdown')];

    function closeDropdowns(except = null) {
        dropdowns.forEach((dropdown) => {
            if (dropdown !== except) dropdown.open = false;
        });
    }

    dropdowns.forEach((dropdown) => {
        dropdown.addEventListener('toggle', () => {
            if (dropdown.open) closeDropdowns(dropdown);
        });
    });

    navigation.addEventListener('click', (event) => {
        if (event.target.closest('a')) closeDropdowns();
    });

    document.addEventListener('click', (event) => {
        if (!navigation.contains(event.target)) closeDropdowns();
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
        if (!openDropdown) return;
        closeDropdowns();
        openDropdown.querySelector('summary').focus();
    });
})();
