// Docs App Logic
document.addEventListener("DOMContentLoaded", () => {
    const dataPromise = fetch('data/reddit_weekly.json?t=' + Date.now()).then(r => r.json());
    const eventsPromise = fetch('data/events.json?t=' + Date.now()).then(r => r.json());

    function getISOWeek(dateString) {
        const d = new Date(dateString);
        if (isNaN(d.getTime())) return null;
        d.setHours(0, 0, 0, 0);
        d.setDate(d.getDate() + 4 - (d.getDay() || 7));
        const yearStart = new Date(d.getFullYear(), 0, 1);
        const weekNo = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
        return `${d.getFullYear()}-W${weekNo.toString().padStart(2, '0')}`;
    }

    Promise.all([dataPromise, eventsPromise])
        .then(([data, events]) => {
            // Use standalone events.json as source of truth for labels/descriptions
            if (events) {
                data.metadata.events = events.map(ev => ({
                    ...ev,
                    iso_week: getISOWeek(ev.date)
                })).filter(ev => ev.iso_week);
            }
            initDashboard(data);
        })
        .catch(err => {
            console.error("Failed to load dashboard data", err);
            document.getElementById('finding-text').innerText = "Data load failed.";
        });
});

function drawEventLines(chartInstance, dates) {
    // Relying on native chart.js annotation plugin configurations implicitly in options.
}

function initDashboard(data) {
    const weekly = data.weekly;
    
    // --- EVERGREEN LOGIC ---
    
    // Helper: Find latest complete week
    const today = new Date();
    const labels = [...new Set(weekly.map(w => w.iso_week))].sort();
    
    function getWeekEndDate(isoStr) {
        const [year, week] = isoStr.split('-W').map(Number);
        const d = new Date(year, 0, 1 + (week - 1) * 7);
        const day = d.getDay();
        const diff = (day <= 4) ? (1 - day) : (8 - day);
        d.setDate(d.getDate() + diff); // ISO Monday
        d.setDate(d.getDate() + 6); // ISO Sunday
        d.setHours(23, 59, 59, 999); // End of Sunday
        return d;
    }

    const completeWeeks = labels.filter(lbl => getWeekEndDate(lbl) < today);
    const latestWeek = completeWeeks[completeWeeks.length - 1];
    const trailingWeeks = completeWeeks.slice(-12, -1); // 11 weeks before latest

    const extractRate = (app, week) => {
        const row = weekly.find(w => w.app === app && w.iso_week === week);
        return row ? (row.harm_rate * 100).toFixed(2) : "0.00";
    };

    const latestRateCai = extractRate("CharacterAI", latestWeek);
    const latestRateRep = extractRate("replika", latestWeek);

    const caiRates = weekly.filter(w => w.app === "CharacterAI").map(w => w.harm_rate * 100);
    const minRateCai = Math.min(...caiRates).toFixed(2);
    const maxRateCai = Math.max(...caiRates).toFixed(2);

    const trailingMeanCai = (weekly
        .filter(w => w.app === "CharacterAI" && trailingWeeks.includes(w.iso_week))
        .reduce((sum, w) => sum + w.harm_rate, 0) / (trailingWeeks.length || 1) * 100).toFixed(2);

    // 1. Render Evergreen Header
    document.getElementById('finding-text').innerHTML = `Harm-language rate in r/CharacterAI, latest complete week (${latestWeek}): <strong>${latestRateCai}%</strong>. Control subreddit r/replika: <strong>${latestRateRep}%</strong>.`;
    
    document.getElementById('evergreen-sub-headline').innerText = `This tracker monitors weekly harm-language rate in the primary Reddit communities for Character.AI and Replika. Rates are the share of weekly submissions containing at least one of 13 pre-registered harm-language terms. Observation window begins August 2024. See methodology below.`;

    document.getElementById('evergreen-context').innerHTML = `Across the full observation window, r/CharacterAI harm-language rate has ranged from <strong>${minRateCai}%</strong> to <strong>${maxRateCai}%</strong>, with an 11-week trailing mean of <strong>${trailingMeanCai}%</strong> (mean of the 11 complete weeks preceding the latest complete week).`;

    // 2. Render Events Table
    const eventsTableContainer = document.getElementById('events-table-container');
    let tableHtml = `
        <table style="width: 100%; border-collapse: collapse; font-size: 0.95rem; background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); border-radius: 6px; overflow: hidden;">
            <thead>
                <tr style="background: var(--surface-2); text-align: left;">
                    <th style="padding: 0.75rem;">Date</th>
                    <th style="padding: 0.75rem;">Event</th>
                    <th style="padding: 0.75rem; text-align: right;">r/CharacterAI Rate</th>
                    <th style="padding: 0.75rem; text-align: right;">r/replika Rate</th>
                </tr>
            </thead>
            <tbody>
    `;

    (data.metadata.events || []).forEach(ev => {
        tableHtml += `
            <tr style="border-bottom: 1px solid var(--border-subtle);">
                <td style="padding: 0.75rem; color: var(--text-secondary);">${ev.date}</td>
                <td style="padding: 0.75rem; font-weight: 500; color: #fff;">${ev.title}</td>
                <td style="padding: 0.75rem; text-align: right; color: #60a5fa; font-weight: 600;">${extractRate("CharacterAI", ev.iso_week)}%</td>
                <td style="padding: 0.75rem; text-align: right; color: #a1a1aa;">${extractRate("replika", ev.iso_week)}%</td>
            </tr>
        `;
    });
    tableHtml += `</tbody></table>`;
    eventsTableContainer.innerHTML = tableHtml;

    // 3. Render Featured Analysis Panel
    const featuredPanel = document.getElementById('featured-analysis-panel');
    const caiAverages = data.averages.CharacterAI;
    const repAverages = data.averages.replika;
    
    featuredPanel.innerHTML = `
        <h4 style="color: #60a5fa; margin-bottom: 1rem; font-size: 1.1rem; display: flex; align-items: center; gap: 0.5rem;">
            <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            Featured analysis: week of October 22, 2024
        </h4>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
            <div>
                <div style="color: #fff; font-size: 1.15rem; font-weight: 700; margin-bottom: 0.5rem;">r/CharacterAI Peak</div>
                <div style="font-size: 0.95rem; color: #d4d4d8; line-height: 1.4;">
                    Rate that week: <strong>3.20%</strong><br>
                    12-week pre-lawsuit mean: ${(caiAverages.pre_harm_rate_mean * 100).toFixed(2)}%<br>
                    12-week post-lawsuit mean: ${(caiAverages.post_harm_rate_mean * 100).toFixed(2)}%
                </div>
            </div>
            <div>
                <div style="color: #fff; font-size: 1.15rem; font-weight: 700; margin-bottom: 0.5rem;">r/replika Control</div>
                <div style="font-size: 0.95rem; color: #d4d4d8; line-height: 1.4;">
                    Rate that week: <strong>0.00%</strong><br>
                    12-week pre-lawsuit mean: ${(repAverages.pre_harm_rate_mean * 100).toFixed(2)}%<br>
                    12-week post-lawsuit mean: ${(repAverages.post_harm_rate_mean * 100).toFixed(2)}%
                </div>
            </div>
        </div>
        <p style="margin-top: 1rem; font-size: 0.9rem; color: var(--text-secondary); font-style: italic; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 0.75rem;">
            This week is the subject of the retrospective analysis in the accompanying paper. See paper for interpretation.
        </p>
    `;

    // --- CHART DATA PREP ---
    function extractSeries(app, metric) {
        return labels.map(lbl => {
            const row = weekly.find(w => w.iso_week === lbl && w.app === app);
            return row ? (row[metric] * (metric.includes('rate') ? 100 : 1)) : 0;
        });
    }

    const caiHarmRate = extractSeries("CharacterAI", "harm_rate");
    const caiVol = extractSeries("CharacterAI", "volume");
    const repHarmRate = extractSeries("replika", "harm_rate");

    // Dynamic Annotations from Metadata
    const annotationsWithLabels = {};
    const annotationsNoLabels = {};
    const yOffsets = [0, 45, 90]; 

    (data.metadata.events || []).forEach((ev, idx) => {
        const base = {
            type: 'line',
            xMin: ev.iso_week,
            xMax: ev.iso_week,
            borderColor: ev.type === 'legal' ? '#f87171' : '#60a5fa',
            borderWidth: 2
        };
        annotationsNoLabels[`ev-${idx}`] = { ...base };
        annotationsWithLabels[`ev-${idx}`] = {
            ...base,
            label: {
                display: true,
                content: ev.title,
                position: 'end',
                yAdjust: yOffsets[idx % 3],
                backgroundColor: 'rgba(0,0,0,0.8)',
                padding: 6,
                font: { family: 'Inter', size: 10, weight: '600' }
            }
        };
    });

    Chart.defaults.color = '#a1a1aa';
    Chart.defaults.font.family = 'Inter';

    const sharedTooltipOptions = {
        callbacks: {
            afterFooter: (context) => {
                const week = context[0].label;
                const ev = (data.metadata.events || []).find(e => e.iso_week === week);
                if (ev) {
                    return `\n${ev.title.toUpperCase()}\n${ev.description}`;
                }
                return '';
            }
        },
        footerFont: { weight: 'normal', size: 11 },
        footerColor: '#60a5fa'
    };

    // PRIMARY CHART: Character.AI
    new Chart(document.getElementById('cai-chart'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Harm-language Rate (%)',
                data: caiHarmRate,
                borderColor: '#60a5fa',
                backgroundColor: 'rgba(96, 165, 250, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.2,
                pointRadius: 2,
                // Partial week distinction
                pointBackgroundColor: (ctx) => {
                    return getWeekEndDate(labels[ctx.dataIndex]) >= today ? 'transparent' : '#60a5fa';
                },
                pointBorderColor: (ctx) => {
                    return getWeekEndDate(labels[ctx.dataIndex]) >= today ? '#60a5fa' : '#60a5fa';
                }
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: 4.0, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false } }
            },
            plugins: {
                annotation: { annotations: annotationsWithLabels },
                legend: { display: false },
                tooltip: sharedTooltipOptions
            }
        }
    });

    // VOLUME CHART: Character.AI
    new Chart(document.getElementById('cai-volume-chart'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Submissions',
                data: caiVol,
                backgroundColor: '#3f3f46'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, display: false },
                x: { display: false }
            },
            plugins: {
                legend: { display: false },
                annotation: { annotations: annotationsNoLabels }
            }
        }
    });

    // CONTROL CHART: Replika
    new Chart(document.getElementById('replika-chart'), {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Harm-language Rate (%)',
                data: repHarmRate,
                borderColor: '#a1a1aa',
                borderWidth: 2,
                tension: 0.2,
                pointRadius: 2,
                // Partial week distinction
                pointBackgroundColor: (ctx) => {
                    return getWeekEndDate(labels[ctx.dataIndex]) >= today ? 'transparent' : '#a1a1aa';
                }
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, max: 4.0, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false } }
            },
            plugins: {
                annotation: { annotations: annotationsWithLabels },
                legend: { display: false },
                tooltip: sharedTooltipOptions
            }
        }
    });

    // --- OTHER UI COMPONENTS ---
    const we = data.metadata.worked_example;
    document.getElementById('worked-example-container').innerHTML = `
        <div style="font-family: monospace; font-size: 0.9rem; color: #d4d4d8;">
            <div style="color: #60a5fa; margin-bottom: 0.25rem;"><strong>Example: Peak Harm Week (r/CharacterAI)</strong></div>
            <div>Target Week: ${we.week}</div>
            <div>Total Submissions: ${we.volume.toLocaleString()}</div>
            <div>Submissions matching harm patterns: ${we.harm_count}</div>
            <div style="margin-top: 0.5rem; border-top: 1px dotted #52525b; padding-top: 0.5rem;">
                <strong>Harm Rate:</strong> (${we.harm_count} / ${we.volume.toLocaleString()}) * 100 = <strong>${(we.harm_rate * 100).toFixed(2)}%</strong>
            </div>
        </div>
    `;

    function createCountTableDom(title, patternsObj) {
        const sorted = Object.entries(patternsObj).sort((a,b) => b[1] - a[1]);
        let rowsHtml = sorted.map(k => `<tr><td style="padding: 0.5rem; border-bottom: 1px solid var(--border-subtle);">${k[0].replace(/\\b/g, '')}</td><td style="padding: 0.5rem; border-bottom: 1px solid var(--border-subtle); text-align: right;">${k[1].toLocaleString()}</td></tr>`).join('');
        return `<div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-subtle); border-radius: 6px; overflow: hidden;"><h3 style="background: var(--surface-2); padding: 0.75rem; margin: 0; font-size: 0.95rem; font-weight: 600; color: #fff;">${title}</h3><table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;"><tbody>${rowsHtml}</tbody></table></div>`;
    }

    const tCont = document.getElementById('pattern-tables-container');
    tCont.innerHTML = createCountTableDom("Character.AI Harm Patterns", data.metadata.pattern_counts.CharacterAI.harm) + createCountTableDom("Character.AI Benefit Patterns", data.metadata.pattern_counts.CharacterAI.benefit) + createCountTableDom("Replika Harm Patterns", data.metadata.pattern_counts.replika.harm) + createCountTableDom("Replika Benefit Patterns", data.metadata.pattern_counts.replika.benefit);

    const eCont = document.getElementById('excerpts-container');
    function getWeekTotalCounts(app, weekStr) {
        const row = weekly.find(w => w.app === app && w.iso_week === weekStr);
        return row || { harm_count: 0, benefit_count: 0 };
    }

    function highlightText(text, patterns) {
        if(!text) return '';
        let highlighted = text;
        patterns.forEach(p => {
            const cleanPat = p.replace(/\\b/g, '');
            const regex = new RegExp(`(${cleanPat})`, 'gi');
            highlighted = highlighted.replace(regex, '<mark style="background: rgba(248, 113, 113, 0.3); color: #fff; padding: 0 2px; border-radius: 2px;">$1</mark>');
        });
        return highlighted;
    }

    function renderQuad(title, dataObj, matchingApp, isHarm) {
        if(!dataObj || !dataObj.week) return '';
        const counts = getWeekTotalCounts(matchingApp, dataObj.week);
        const matchTotal = isHarm ? counts.harm_count : counts.benefit_count;
        
        let headerNote = matchTotal < 10 ? ` <span style="color: #f87171; font-weight: 500;">(${matchTotal} matching submissions — low volume, interpret with caution)</span>` : ` <span style="color: var(--text-secondary);">(${matchTotal.toLocaleString()} matching submissions in week)</span>`;

        let postsHtml = dataObj.posts.map(p => {
             const highlightedBody = highlightText(p.selftext, p.patterns_matched || []);
             const highlightedTitle = highlightText(p.title, p.patterns_matched || []);
             return `
                <div style="margin-bottom: 1.5rem; padding-left: 1rem; border-left: 2px solid ${isHarm ? '#f87171' : '#4ade80'};">
                    <div style="font-weight: 600; color: #fff; margin-bottom: 0.25rem;">${highlightedTitle || '<em>(No Title)</em>'}</div>
                    <div style="color: #d4d4d8; font-size: 0.95rem;">${highlightedBody ? `"${highlightedBody}"` : '<em>(No body text)</em>'}</div>
                    <div style="font-size: 0.8rem; color: #71717a; margin-top: 0.25rem;">${p.date} • <a href="https://reddit.com${p.permalink}" target="_blank" style="color: #60a5fa; text-decoration: none;">View Original</a></div>
                </div>
             `;
        }).join('');

        const captionText = isHarm ? "First five matching submissions by timestamp. Matches may include casual use, roleplay framing, or negation. No manual curation." : "First five matching submissions by timestamp. Some posts use terms like 'support' or 'help' in customer-support contexts rather than emotional-support contexts. No manual curation.";

        return `
            <div style="background: var(--surface-1); padding: 1.5rem; border: 1px solid var(--border-subtle); border-radius: 8px;">
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem; font-weight: 400;">${captionText}</div>
                <h3 style="font-size: 1.1rem; color: #fff; margin-bottom: 1.5rem;">${title}: ${dataObj.week}${headerNote}</h3>
                ${postsHtml}
            </div>
        `;
    }

    eCont.innerHTML = renderQuad("Peak harm week, r/CharacterAI", data.metadata.excerpts.CharacterAI_harm, "CharacterAI", true) + renderQuad("Peak benefit week, r/CharacterAI", data.metadata.excerpts.CharacterAI_benefit, "CharacterAI", false) + renderQuad("Peak harm week, r/replika", data.metadata.excerpts.replika_harm, "replika", true) + renderQuad("Peak benefit week, r/replika", data.metadata.excerpts.replika_benefit, "replika", false);
}
