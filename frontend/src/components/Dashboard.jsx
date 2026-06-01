import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  Brain,
  User,
  BookOpen,
  Sparkles,
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  RefreshCw,
  Award,
} from 'lucide-react';
import './Dashboard.css';

// Default mock stats to guarantee a premium fallback experience
const DEFAULT_STATS = {
  humanScoreBefore: 12,
  humanScoreAfter: 98,
  aiScoreBefore: 88,
  aiScoreAfter: 2,
  
  vocabBefore: 45,
  vocabAfter: 88,
  
  readEaseBefore: 32,
  readEaseAfter: 78,
  
  complexityBefore: 85,
  complexityAfter: 48, // Lower is simpler/more natural
  
  sentenceVarietyBefore: 28,
  sentenceVarietyAfter: 84,
  
  wordCountOriginal: 412,
  wordCountHumanized: 435,
  gradeBefore: 'Graduate Level',
  gradeAfter: '7th Grade (Perfect for Web)',
};

// Custom tooltips for Recharts matching deep slate dark-theme
const CustomPieTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="custom-tooltip">
        <div className="tooltip-title">{data.name}</div>
        <div className="tooltip-item">
          <span className="tooltip-dot" style={{ backgroundColor: data.color }} />
          <span style={{ color: 'var(--text-secondary)' }}>Ratio:</span>
          <strong style={{ color: 'var(--text-vivid)', marginLeft: 'auto', paddingLeft: '8px' }}>{data.value}%</strong>
        </div>
      </div>
    );
  }
  return null;
};

const CustomBarTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip">
        <div className="tooltip-title">{label}</div>
        {payload.map((item, idx) => (
          <div key={idx} className="tooltip-item">
            <span className="tooltip-dot" style={{ backgroundColor: idx === 0 ? '#818cf8' : 'var(--purple-accent)' }} />
            <span style={{ color: 'var(--text-secondary)' }}>{item.name}:</span>
            <strong style={{ color: 'var(--text-vivid)', marginLeft: 'auto', paddingLeft: '8px' }}>{item.value}/100</strong>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

// Premium Speedometer Gauge Component
function Speedometer({ score, title }) {
  // Map score (0-100) to rotation angle (-90deg to 90deg for a half-circle)
  const angle = (score / 100) * 180 - 90;
  
  let color = '#10b981'; // Emerald Green (passed/low risk)
  let label = 'LOW DETECTION';
  if (score > 60) {
    color = '#f43f5e'; // Crimson Red (high risk)
    label = 'HIGH RISK';
  } else if (score > 30) {
    color = '#f59e0b'; // Amber Yellow (medium risk)
    label = 'MODERATE';
  }
  
  return (
    <div className="speedometer-gauge-card">
      <h5>{title}</h5>
      <div className="speedometer-wrapper">
        <svg width="200" height="120" viewBox="0 0 200 120">
          {/* Background track */}
          <path
            d="M20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth="10"
            strokeLinecap="round"
          />
          {/* Active indicator arc */}
          <path
            d="M20 100 A 80 80 0 0 1 180 100"
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray="251.2"
            strokeDashoffset={251.2 - (score / 100) * 251.2}
            style={{ transition: 'stroke-dashoffset 1.5s ease-in-out, stroke 1.5s' }}
          />
          {/* Gauge Center Pin */}
          <circle cx="100" cy="100" r="6" fill="#f8fafc" />
          {/* Pointer Needle */}
          <line
            x1="100"
            y1="100"
            x2="100"
            y2="40"
            stroke="#f8fafc"
            strokeWidth="3.5"
            strokeLinecap="round"
            style={{
              transform: `rotate(${angle}deg)`,
              transformOrigin: '100px 100px',
              transition: 'transform 1.8s cubic-bezier(0.34, 1.56, 0.64, 1)'
            }}
          />
        </svg>
        <div className="speedometer-info">
          <span className="speedometer-value" style={{ color }}>{score}%</span>
          <span className="speedometer-label" style={{ color }}>{label}</span>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard({ stats: propStats }) {
  const stats = { ...DEFAULT_STATS, ...(propStats || {}) };
  const humanDiff = (stats.humanScoreAfter ?? 0) - (stats.humanScoreBefore ?? 0);
  const aiDiff = (stats.aiScoreBefore ?? 0) - (stats.aiScoreAfter ?? 0); // Positive means AI score decreased (good!)

  // Pie chart data formats
  const pieDataBefore = [
    { name: 'Human Content', value: stats.humanScoreBefore, color: '#10b981' },
    { name: 'AI Footprint', value: stats.aiScoreBefore, color: '#f43f5e' },
  ];

  const pieDataAfter = [
    { name: 'Human Content', value: stats.humanScoreAfter, color: '#10b981' },
    { name: 'AI Footprint', value: stats.aiScoreAfter, color: '#f43f5e' },
  ];

  // Bar chart data format comparing structural statistics
  const styleComparisonData = [
    {
      name: 'Vocabulary Diversity',
      Before: stats.vocabBefore,
      After: stats.vocabAfter,
    },
    {
      name: 'Reading Accessibility',
      Before: stats.readEaseBefore,
      After: stats.readEaseAfter,
    },
    {
      name: 'Sentence Variety',
      Before: stats.sentenceVarietyBefore,
      After: stats.sentenceVarietyAfter,
    },
    {
      name: 'Structural Complexity',
      Before: stats.complexityBefore,
      After: stats.complexityAfter,
    },
  ];

  // Trend color resolver
  const getTrendClass = (before, after, invert = false) => {
    const isImproved = invert ? after < before : after > before;
    if (before === after) return 'trend-neutral';
    return isImproved ? 'trend-up' : 'trend-down';
  };

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div className="dashboard-title-area">
          <h3>
            <Sparkles size={20} className="inline mr-2 text-purple-500 animate-pulse" style={{ display: 'inline', marginRight: '6px', color: 'var(--purple-accent)' }} />
            Transformation Analytics
          </h3>
          <p>Comparative linguistic analysis of your content before and after humanization</p>
        </div>
        <div className="dashboard-actions">
          <button className="dashboard-btn" onClick={() => window.print()}>
            Export PDF
          </button>
        </div>
      </div>

      {/* Metric Cards Row - Premium Glowing Number Boxes */}
      <div className="metrics-grid">
        {/* Metric 1: Human Match */}
        <div className="metric-card success">
          <div className="metric-header">
            <span>HUMAN SCORE</span>
            <div className="metric-icon-wrapper">
              <User size={16} />
            </div>
          </div>
          <div>
            <div className="metric-comparison">
              <span className="metric-number">{stats.humanScoreAfter}%</span>
              <span className="text-xs text-slate-400" style={{ color: 'var(--text-secondary)' }}>
                was {stats.humanScoreBefore}%
              </span>
            </div>
            <div className="metric-label">
              <span className={`trend-indicator ${getTrendClass(stats.humanScoreBefore, stats.humanScoreAfter)}`}>
                {humanDiff >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                {humanDiff >= 0 ? '+' : ''}{humanDiff.toFixed(1)}% Humanized
              </span>
            </div>
          </div>
        </div>

        {/* Metric 2: AI Probability */}
        <div className="metric-card danger">
          <div className="metric-header">
            <span>AI DETECTION INDEX</span>
            <div className="metric-icon-wrapper">
              <Brain size={16} />
            </div>
          </div>
          <div>
            <div className="metric-comparison">
              <span className="metric-number">
                {stats.aiScoreAfter}%
              </span>
              <span className="text-xs text-slate-400" style={{ color: 'var(--text-secondary)' }}>
                was {stats.aiScoreBefore}%
              </span>
            </div>
            <div className="metric-label">
              <span className={`trend-indicator ${getTrendClass(stats.aiScoreBefore, stats.aiScoreAfter, true)}`}>
                {aiDiff >= 0 ? <ArrowDownRight size={12} /> : <ArrowUpRight size={12} />}
                {aiDiff >= 0 ? '-' : '+'}{Math.abs(aiDiff).toFixed(1)}% Footprint
              </span>
            </div>
          </div>
        </div>

        {/* Metric 3: Readability Grade */}
        <div className="metric-card accent">
          <div className="metric-header">
            <span>COMPREHENSION LEVEL</span>
            <div className="metric-icon-wrapper">
              <BookOpen size={16} />
            </div>
          </div>
          <div>
            <div className="metric-comparison">
              <span className="metric-number metric-text-value" title={stats.gradeAfter}>
                {stats.gradeAfter}
              </span>
            </div>
            <div className="text-xs text-slate-400" style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: '0.25rem' }}>
              was {stats.gradeBefore}
            </div>
            <div className="metric-label">
              <span className="trend-indicator trend-up">
                <TrendingUp size={12} />
                Natural Flow
              </span>
            </div>
          </div>
        </div>

        {/* Metric 4: Word Counts & Expansion */}
        <div className="metric-card accent">
          <div className="metric-header">
            <span>CONTENT LENGTH</span>
            <div className="metric-icon-wrapper">
              <Award size={16} />
            </div>
          </div>
          <div>
            <div className="metric-comparison">
              <span className="metric-number">{stats.wordCountHumanized}</span>
              <span className="text-xs text-slate-400" style={{ color: 'var(--text-secondary)' }}>
                words (was {stats.wordCountOriginal})
              </span>
            </div>
            <div className="metric-label">
              <span className="trend-indicator trend-neutral" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <RefreshCw size={10} className="animate-spin" style={{ animationDuration: '4s' }} />
                +{Math.max(0, stats.wordCountHumanized - stats.wordCountOriginal)} words added for rhythm
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Layout Grid */}
      <div className="charts-grid">
        {/* Card 1: Plagiarism & AI Risk Speedometer Gauges */}
        <div className="chart-card">
          <div className="chart-header">
            <div className="chart-title">
              <h4>Detection Risk Profile</h4>
              <p>Real-time AI detection index metrics comparison</p>
            </div>
          </div>
          
          <div className="speedometers-container">
            <Speedometer score={stats.aiScoreBefore} title="Original Draft" />
            <Speedometer score={stats.aiScoreAfter} title="Humanized Output" />
          </div>

          <div className="chart-legend-custom" style={{ marginTop: '0.25rem' }}>
            <div className="legend-item">
              <span className="legend-color-box" style={{ backgroundColor: '#f43f5e' }} />
              <span>High Risk (&gt;60% AI likelihood)</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-box" style={{ backgroundColor: '#f59e0b' }} />
              <span>Moderate Risk (30% - 60%)</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-box" style={{ backgroundColor: '#10b981' }} />
              <span>Low Risk / Human Passed (&lt;30%)</span>
            </div>
          </div>
        </div>

        {/* Card 2: Grouped Bar Chart comparing Style & Readability */}
        <div className="chart-card">
          <div className="chart-header">
            <div className="chart-title">
              <h4>Linguistic Qualities</h4>
              <p>Comparative score metrics (out of 100) before and after optimization</p>
            </div>
          </div>

          <div style={{ width: '100%', height: 210 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={styleComparisonData}
                margin={{ top: 10, right: 10, left: -25, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-glass)" />
                <XAxis 
                  dataKey="name" 
                  tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontWeight: 500 }} 
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis 
                  domain={[0, 100]} 
                  tick={{ fill: 'var(--text-secondary)', fontSize: 10, fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<CustomBarTooltip />} cursor={{ fill: 'rgba(255, 255, 255, 0.03)' }} />
                <Bar dataKey="Before" fill="#818cf8" radius={[4, 4, 0, 0]}>
                  {styleComparisonData.map((entry, index) => (
                    <Cell key={`cell-before-${index}`} fill="#818cf8" />
                  ))}
                </Bar>
                <Bar dataKey="After" fill="var(--purple-accent)" radius={[4, 4, 0, 0]}>
                  {styleComparisonData.map((entry, index) => (
                    <Cell key={`cell-after-${index}`} fill="var(--purple-accent)" />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Bar Chart Legend */}
          <div className="chart-legend-custom" style={{ marginTop: '0.15rem' }}>
            <div className="legend-item">
              <span className="legend-color-box" style={{ backgroundColor: '#818cf8' }} />
              <span>Original (Standard AI Output)</span>
            </div>
            <div className="legend-item">
              <span className="legend-color-box" style={{ backgroundColor: 'var(--purple-accent)' }} />
              <span>Humanized (Vivid, Dynamic Style)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
