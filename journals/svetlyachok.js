// The complete archive is rendered in the HTML; these controls enhance it
// without making the issue links dependent on JavaScript.
(() => {
    const controls = document.getElementById('journalControls');
    const years = document.getElementById('yearNavigation');
    const search = document.getElementById('searchInput');
    const clear = document.getElementById('clearSearchBtn');
    const reset = document.getElementById('emptyResetBtn');
    const subtitle = document.getElementById('pageSubtitle');
    const status = document.getElementById('journalStatus');
    const empty = document.getElementById('emptyState');
    const grid = document.getElementById('issuesGrid');
    if (!controls || !years || !search || !clear || !reset || !subtitle || !status || !empty || !grid) return;

    const MIN_YEAR = 2011;
    const MAX_YEAR = 2026;
    const allIssues = [...grid.querySelectorAll('[data-issue-number]')].map((card) => {
        const startYear = Number(card.dataset.startYear);
        const endYear = Number(card.dataset.endYear);
        const periodByYear = {
            [startYear]: card.dataset.startPeriod,
            [endYear]: card.dataset.endPeriod,
        };
        const issue = {
            card,
            number: Number(card.dataset.issueNumber),
            startYear,
            endYear,
            period: card.dataset.period,
            periodByYear,
        };
        const text = [
            card.querySelector('h2').textContent,
            issue.period,
            ...Object.values(periodByYear),
        ].join(' ').toLowerCase().replace(/ё/g, 'е');
        const seasons = [];
        if (/(декабр|январ|феврал|зим)/.test(text)) seasons.push('зима зимний');
        if (/(март|апрел|май|весн)/.test(text)) seasons.push('весна весенний');
        if (/(июн|июл|август|лет)/.test(text)) seasons.push('лето летний');
        if (/(сентябр|октябр|ноябр|осен)/.test(text)) seasons.push('осень осенний');
        issue.searchText = `${text} ${seasons.join(' ')}`;
        return issue;
    });
    if (!allIssues.length) return;

    function yearFromHash() {
        const hash = window.location.hash.match(/^#(\d{4})$/);
        const year = hash ? Number(hash[1]) : null;
        return year !== null && year >= MIN_YEAR && year <= MAX_YEAR ? year : null;
    }
    let selectedYear = yearFromHash() ?? MIN_YEAR;

    function pluralizeIssues(n) {
        const mod10 = n % 10;
        const mod100 = n % 100;
        if (mod10 === 1 && mod100 !== 11) return `${n} выпуск`;
        if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${n} выпуска`;
        return `${n} выпусков`;
    }

    function parseSearchQuery(raw) {
        let query = raw.trim().toLowerCase().replace(/ё/g, 'е');
        if (!query) return null;

        const foundYears = [];
        let partialEndYearPrefix = null;
        query = query.replace(/\b(19\d{2}|20\d{2})\s*[-–—/\\]\s*(\d{1,3})(?!\d)/g, (match, y1Str, y2Part) => {
            const y1 = Number(y1Str);
            if (y2Part.length === 2) {
                const fullY2 = 2000 + Number(y2Part);
                if (fullY2 >= y1 && fullY2 <= y1 + 5 && y2Part !== '20') {
                    foundYears.push(y1, fullY2);
                    return ' ';
                }
            }
            if ('201'.startsWith(y2Part) || '202'.startsWith(y2Part)) {
                foundYears.push(y1);
                partialEndYearPrefix = y2Part;
                return ' ';
            }
            return match;
        });

        query = query.replace(/(?:^|\D)(19\d{2}|20\d{2})(?=\D|$)/g, (match, year) => {
            foundYears.push(Number(year));
            return ' ';
        });

        const issueNumbers = [];
        query = query.replace(/\b\d+\s*\(\s*(\d{1,3})\s*\)/g, (_, number) => {
            issueNumbers.push(Number(number));
            return ' ';
        });

        let yearPrefix = null;
        query = query.replace(/\d+/g, (number) => {
            if (number.length === 3 && (number.startsWith('201') || number.startsWith('202'))) {
                yearPrefix = number;
            } else {
                issueNumbers.push(Number(number));
            }
            return ' ';
        });

        const stopWords = new Set([
            '№', '#', 'n', 'no', 'выпуск', 'выпуска', 'выпуски', 'номер',
            'журнал', 'журнала', 'светлячок', 'год', 'года', 'году', 'годы',
            'г', 'гг', 'за', 'с', 'по', 'и', 'в', 'на',
        ]);
        const textTokens = query
            .replace(/[«»"'.,:;!?()\[\]{}\/\\—–-]+/g, ' ')
            .split(/\s+/)
            .filter((token) => token.length > 0 && !stopWords.has(token));

        return { years: foundYears, partialEndYearPrefix, yearPrefix, issueNumbers, textTokens };
    }

    function filterIssues(parsed) {
        const { years: foundYears, partialEndYearPrefix, yearPrefix, issueNumbers, textTokens } = parsed;
        const minYear = foundYears.length >= 2 ? Math.min(foundYears[0], foundYears[1]) : null;
        const maxYear = foundYears.length >= 2 ? Math.max(foundYears[0], foundYears[1]) : null;
        const hasExactDualIssue = minYear !== null && minYear !== maxYear && allIssues.some(
            (issue) => issue.startYear === minYear && issue.endYear === maxYear,
        );

        return allIssues.filter((issue) => {
            if (issueNumbers.length && !issueNumbers.includes(issue.number)) return false;
            if (yearPrefix && !String(issue.startYear).startsWith(yearPrefix) &&
                !String(issue.endYear).startsWith(yearPrefix)) return false;
            if (minYear !== null && minYear !== maxYear) {
                if (hasExactDualIssue) {
                    if (issue.startYear !== minYear || issue.endYear !== maxYear) return false;
                } else if (issue.endYear < minYear || issue.startYear > maxYear) {
                    return false;
                }
            } else if (foundYears.length) {
                const year = foundYears[0];
                if (partialEndYearPrefix) {
                    if (!((issue.startYear === year || issue.endYear === year) &&
                        String(issue.endYear).startsWith(partialEndYearPrefix))) return false;
                } else if (issue.startYear !== year && issue.endYear !== year) {
                    return false;
                }
            }
            return textTokens.every((token) => issue.searchText.includes(token));
        });
    }

    function render() {
        const query = search.value;
        const parsed = parseSearchQuery(query);
        clear.hidden = !query.length;
        let visible;
        let contextYear;
        let highlightedYear;

        if (parsed) {
            visible = filterIssues(parsed);
            contextYear = parsed.years.length === 1 && !parsed.partialEndYearPrefix ? parsed.years[0] : null;
            const onlyOneYear = parsed.years.length === 1 && !parsed.partialEndYearPrefix && !parsed.yearPrefix &&
                !parsed.issueNumbers.length && !parsed.textTokens.length;
            highlightedYear = onlyOneYear ? parsed.years[0] : null;
            subtitle.textContent = 'Результаты поиска';
            status.textContent = `Найдено: ${pluralizeIssues(visible.length)}`;
        } else {
            visible = allIssues.filter((issue) => issue.startYear === selectedYear || issue.endYear === selectedYear);
            contextYear = selectedYear;
            highlightedYear = selectedYear;
            subtitle.textContent = `${selectedYear} год`;
            status.textContent = pluralizeIssues(visible.length);
        }

        const visibleCards = new Set(visible);
        allIssues.forEach((issue) => {
            issue.card.hidden = !visibleCards.has(issue);
            issue.card.querySelector('.journal-period').textContent =
                (contextYear && issue.periodByYear[contextYear]) || issue.period;
        });
        years.querySelectorAll('button').forEach((button) => {
            button.setAttribute('aria-pressed', String(Number(button.dataset.year) === highlightedYear));
        });
        empty.hidden = visible.length !== 0;
    }

    for (let year = MIN_YEAR; year <= MAX_YEAR; year++) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'year-btn';
        button.dataset.year = String(year);
        button.textContent = String(year);
        button.setAttribute('aria-pressed', 'false');
        button.addEventListener('click', () => {
            selectedYear = year;
            search.value = '';
            render();
        });
        years.appendChild(button);
    }

    search.addEventListener('input', render);
    function clearSearch() {
        search.value = '';
        search.focus();
        render();
    }
    clear.addEventListener('click', clearSearch);
    reset.addEventListener('click', clearSearch);
    window.addEventListener('hashchange', () => {
        const year = yearFromHash();
        if (year !== null) {
            selectedYear = year;
            search.value = '';
            render();
        }
    });
    controls.hidden = false;
    render();
})();
