/**
 * AI Companion Narrative Shift Tracker — Dashboard Logic
 * Fetches CSV data from the repo, parses it, and renders Chart.js visualizations.
 * Fully autonomous — no manual configuration needed.
 */

// ============================================================
// Configuration
// ============================================================

// When deployed on GitHub Pages, CSVs are accessible via relative path.
// In development, point these to the raw GitHub URLs if needed.
const DATA_BASE = '../data';
const APPSTORE_CSV_URL = `${DATA_BASE}/appstore_weekly.csv`;
const REDDIT_CSV_URL = `${DATA_BASE}/reddit_weekly.csv`;

// Color palette for chart lines/bars
const APP_COLORS = {
    character_ai: { line: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.12)' },
    replika:      { line: '#60a5fa', bg: 'rgba(96, 165, 250, 0.12)' },
    pi:           { line: '#34d399', bg: 'rgba(52, 211, 153, 0.12)' },
    woebot:       { line: '#fbbf24', bg: 'rgba(251, 191, 36, 0.12)' },
};

const SUBREDDIT_COLORS = {
    replika:      { line: '#60a5fa', bg: 'rgba(96, 165, 250, 0.12)' },
    CharacterAI:  { line: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.12)' },
    artificial:   { line: '#f472b6', bg: 'rgba(244, 114, 182, 0.12)' },
};

// Chart.js global defaults
Chart.defaults.color = '#8888a8';
Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.04)';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyle = 'circle';
Chart.defaults.plugins.legend.labels.padding = 16;
Chart.defaults.elements.line.tension = 0.35;
Chart.defaults.elements.line.borderWidth = 2.5;
Chart.defaults.elements.point.radius = 3;
Chart.defaults.elements.point.hoverRadius = 6;
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;

// ============================================================
// CSV Parser (lightweight, no dependencies)
// ============================================================

function parseCSV(text) {
    const lines = text.trim().split('\n');
    if (lines.length < 2) return [];

    const headers = lines[0].split(',').map(h => h.trim());
    return lines.slice(1).map(line => {
        const values = line.split(',').map(v => v.trim());
        const obj = {};
        headers.forEach((h, i) => {
            const val = values[i] || '';
            // Auto-convert numbers
            obj[h] = isNaN(val) || val === '' ? val : parseFloat(val);
        });
        return obj;
    });
}

// ============================================================
// Data Fetching
// ============================================================

async function fetchCSV(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const text = await response.text();
        return parseCSV(text);
    } catch (err) {
        console.warn(`Failed to fetch ${url}:`, err.message);
        return [];
    }
}

// ============================================================
// Stats Computation
// ============================================================

function computeStats(appstoreData, redditData) {
    const totalReviews = appstoreData.reduce((sum, r) => sum + (r.review_count || 0), 0);
    const totalRedditPosts = redditData.reduce((sum, r) => sum + (r.post_count || 0) + (r.comment_count || 0), 0);

    const avgBenefit = appstoreData.length > 0
        ? (appstoreData.reduce((sum, r) => sum + (r.benefit_rate || 0), 0) / appstoreData.length * 100).toFixed(1)
        : '—';

    const avgHarm = appstoreData.length > 0
        ? (appstoreData.reduce((sum, r) => sum + (r.harm_rate || 0), 0) / appstoreData.length * 100).toFixed(1)
        : '—';

    const weeks = new Set([
        ...appstoreData.map(r => r.week),
        ...redditData.map(r => r.week),
    ]).size;

    return {
        totalReviews: totalReviews + totalRedditPosts,
        avgBenefit: avgBenefit === '—' ? '—' : `${avgBenefit}%`,
        avgHarm: avgHarm === '—' ? '—' : `${avgHarm}%`,
        weeksTracked: weeks || '—',
    };
}

function updateStatsUI(stats) {
    document.getElementById('total-reviews-value').textContent = 
        typeof stats.totalReviews === 'number' ? stats.totalReviews.toLocaleString() : stats.totalReviews;
    document.getElementById('avg-benefit-value').textContent = stats.avgBenefit;
    document.getElementById('avg-harm-value').textContent = stats.avgHarm;
    document.getElementById('weeks-tracked-value').textContent = stats.weeksTracked;
}

// ============================================================
// Chart Builders
// ============================================================

function groupByEntity(data, entityKey) {
    const groups = {};
    data.forEach(row => {
        const key = row[entityKey];
        if (!groups[key]) groups[key] = [];
        groups[key].push(row);
    });
    // Sort each group by week
    Object.values(groups).forEach(arr => arr.sort((a, b) => a.week.localeCompare(b.week)));
    return groups;
}

function buildLineChart(canvasId, data, entityKey, valueKey, colorMap, yLabel = '') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const groups = groupByEntity(data, entityKey);
    const allWeeks = [...new Set(data.map(r => r.week))].sort();

    const datasets = Object.entries(groups).map(([name, rows]) => {
        const colors = colorMap[name] || { line: '#888', bg: 'rgba(136,136,136,0.1)' };
        const weekMap = Object.fromEntries(rows.map(r => [r.week, r[valueKey]]));
        return {
            label: name,
            data: allWeeks.map(w => weekMap[w] ?? null),
            borderColor: colors.line,
            backgroundColor: colors.bg,
            fill: true,
            spanGaps: true,
        };
    });

    new Chart(ctx, {
        type: 'line',
        data: { labels: allWeeks, datasets },
        options: {
            plugins: {
                tooltip: {
                    backgroundColor: 'rgba(18, 18, 30, 0.95)',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    titleFont: { weight: '600' },
                    padding: 12,
                    cornerRadius: 10,
                },
            },
            scales: {
                y: {
                    title: { display: !!yLabel, text: yLabel, color: '#8888a8' },
                    grid: { color: 'rgba(255,255,255,0.03)' },
                },
                x: {
                    grid: { display: false },
                },
            },
        },
    });
}

function buildBarChart(canvasId, data, entityKey, valueKey, colorMap) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const groups = groupByEntity(data, entityKey);
    const allWeeks = [...new Set(data.map(r => r.week))].sort();

    const datasets = Object.entries(groups).map(([name, rows]) => {
        const colors = colorMap[name] || { line: '#888', bg: 'rgba(136,136,136,0.3)' };
        const weekMap = Object.fromEntries(rows.map(r => [r.week, r[valueKey]]));
        return {
            label: name,
            data: allWeeks.map(w => weekMap[w] ?? 0),
            backgroundColor: colors.line + '88',
            borderColor: colors.line,
            borderWidth: 1,
            borderRadius: 4,
        };
    });

    new Chart(ctx, {
        type: 'bar',
        data: { labels: allWeeks, datasets },
        options: {
            plugins: {
                tooltip: {
                    backgroundColor: 'rgba(18, 18, 30, 0.95)',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                },
            },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.03)' }, beginAtZero: true },
                x: { grid: { display: false } },
            },
        },
    });
}

function buildDualRateChart(canvasId, data, entityKey, colorMap) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const groups = groupByEntity(data, entityKey);
    const allWeeks = [...new Set(data.map(r => r.week))].sort();
    const datasets = [];

    Object.entries(groups).forEach(([name, rows]) => {
        const weekMap = Object.fromEntries(rows.map(r => [r.week, r]));

        datasets.push({
            label: `${name} (benefit)`,
            data: allWeeks.map(w => weekMap[w]?.benefit_rate ?? null),
            borderColor: '#34d399',
            backgroundColor: 'rgba(52, 211, 153, 0.08)',
            fill: false,
            spanGaps: true,
            borderDash: name !== Object.keys(groups)[0] ? [5, 5] : [],
        });

        datasets.push({
            label: `${name} (harm)`,
            data: allWeeks.map(w => weekMap[w]?.harm_rate ?? null),
            borderColor: '#f87171',
            backgroundColor: 'rgba(248, 113, 113, 0.08)',
            fill: false,
            spanGaps: true,
            borderDash: name !== Object.keys(groups)[0] ? [5, 5] : [],
        });
    });

    new Chart(ctx, {
        type: 'line',
        data: { labels: allWeeks, datasets },
        options: {
            plugins: {
                tooltip: {
                    backgroundColor: 'rgba(18, 18, 30, 0.95)',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                },
            },
            scales: {
                y: {
                    title: { display: true, text: 'Rate', color: '#8888a8' },
                    grid: { color: 'rgba(255,255,255,0.03)' },
                    min: 0,
                    max: 1,
                },
                x: { grid: { display: false } },
            },
        },
    });
}

// ============================================================
// Reddit-specific volume chart (posts + comments stacked)
// ============================================================

function buildRedditVolumeChart(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const groups = groupByEntity(data, 'subreddit');
    const allWeeks = [...new Set(data.map(r => r.week))].sort();

    const datasets = Object.entries(groups).map(([name, rows]) => {
        const colors = SUBREDDIT_COLORS[name] || { line: '#888' };
        const weekMap = Object.fromEntries(rows.map(r => [r.week, (r.post_count || 0) + (r.comment_count || 0)]));
        return {
            label: `r/${name}`,
            data: allWeeks.map(w => weekMap[w] ?? 0),
            backgroundColor: colors.line + '88',
            borderColor: colors.line,
            borderWidth: 1,
            borderRadius: 4,
        };
    });

    new Chart(ctx, {
        type: 'bar',
        data: { labels: allWeeks, datasets },
        options: {
            plugins: {
                tooltip: {
                    backgroundColor: 'rgba(18, 18, 30, 0.95)',
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 10,
                },
            },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.03)' }, beginAtZero: true, stacked: false },
                x: { grid: { display: false } },
            },
        },
    });
}

// ============================================================
// Main Init
// ============================================================

async function init() {
    console.log('[Tracker] Loading data...');

    const [appstoreData, redditData] = await Promise.all([
        fetchCSV(APPSTORE_CSV_URL),
        fetchCSV(REDDIT_CSV_URL),
    ]);

    console.log(`[Tracker] App Store rows: ${appstoreData.length}, Reddit rows: ${redditData.length}`);

    // Show no-data overlay if both are empty
    const overlay = document.getElementById('no-data-overlay');
    if (appstoreData.length === 0 && redditData.length === 0) {
        overlay?.classList.remove('hidden');
        return;
    }
    overlay?.classList.add('hidden');

    // Update stats
    const stats = computeStats(appstoreData, redditData);
    updateStatsUI(stats);

    // Build App Store charts
    if (appstoreData.length > 0) {
        buildLineChart('appstore-sentiment-chart', appstoreData, 'app', 'net_sentiment', APP_COLORS, 'Net Sentiment');
        buildDualRateChart('appstore-rates-chart', appstoreData, 'app', APP_COLORS);
        buildBarChart('appstore-volume-chart', appstoreData, 'app', 'review_count', APP_COLORS);
    }

    // Build Reddit charts
    if (redditData.length > 0) {
        buildLineChart('reddit-sentiment-chart', redditData, 'subreddit', 'net_sentiment', SUBREDDIT_COLORS, 'Net Sentiment');
        buildLineChart('reddit-velocity-chart', redditData, 'subreddit', 'sentiment_velocity', SUBREDDIT_COLORS, 'Velocity');
        buildRedditVolumeChart('reddit-volume-chart', redditData);
    }

    console.log('[Tracker] Dashboard ready.');
}

// Run on DOM ready
document.addEventListener('DOMContentLoaded', init);
