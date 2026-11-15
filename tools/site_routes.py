"""Human-readable public URLs and their source HTML files.

GitHub Pages serves ``name.html`` at ``/name`` as well as ``/name.html``.
Keep the source paths here so the build can make the extensionless URLs
without maintaining duplicate page content.
"""

ROUTES = {
    "/главная": "index.html",
    "/светлячок": "journals/svetlyachok.html",
    "/медиасобытия/волга-юнпресс": "journals/volga-yunpress.html",
    "/media-camp": "journals/media-camp.html",
    "/48-ая-волна": "journals/48-volna.html",
    "/глобус": "journals/globus.html",
    "/проекты/мх-кряк": "projects/kryak.html",
    "/проекты/медиазавры-вперёд": "projects/mediazavry.html",
}
