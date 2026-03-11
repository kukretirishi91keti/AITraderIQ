/**
 * SentimentDashboard - Combined sentiment from Reddit, StockTwits, and News.
 * Shows composite score, source breakdown, and sample posts.
 */
import React, { useState, useEffect, memo } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const SCORE_COLORS = {
  VERY_BULLISH: 'text-green-400',
  BULLISH: 'text-green-400',
  NEUTRAL: 'text-gray-400',
  BEARISH: 'text-red-400',
  VERY_BEARISH: 'text-red-400',
};

const SCORE_BG = {
  VERY_BULLISH: 'bg-green-900/30',
  BULLISH: 'bg-green-900/20',
  NEUTRAL: 'bg-gray-800/50',
  BEARISH: 'bg-red-900/20',
  VERY_BEARISH: 'bg-red-900/30',
};

function SentimentDashboard({ symbol }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!symbol) return;
    fetchSentiment();
  }, [symbol]);

  const fetchSentiment = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/sentiment/combined/${symbol}`);
      const json = await res.json();
      if (json.success) setData(json);
    } catch (e) {
      console.error('Sentiment fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="p-4 text-center text-gray-400">Loading sentiment...</div>;
  }

  if (!data) {
    return <div className="p-4 text-center text-gray-500">No sentiment data</div>;
  }

  return (
    <div className="space-y-4">
      {/* Composite Score */}
      <div className={`rounded-lg p-4 text-center ${SCORE_BG[data.label] || 'bg-gray-800/50'}`}>
        <div className="text-3xl font-bold">
          <span className={SCORE_COLORS[data.label] || 'text-white'}>
            {data.composite_score > 0 ? '+' : ''}{data.composite_score}
          </span>
        </div>
        <div className={`text-sm font-medium ${SCORE_COLORS[data.label] || 'text-gray-400'}`}>
          {data.label?.replace('_', ' ')}
        </div>
        <div className="text-xs text-gray-500 mt-1">
          {data.confidence}% confidence | Sources {data.agreement?.toLowerCase()}
        </div>
        <div className="text-xs mt-2 text-gray-400">{data.recommendation_text}</div>
      </div>

      {/* Source Breakdown */}
      <div className="grid grid-cols-3 gap-2">
        {Object.entries(data.sources || {}).map(([name, source]) => (
          <SourceCard key={name} name={name} source={source} />
        ))}
      </div>

      {/* Sample Posts */}
      <div className="bg-gray-800/50 rounded-lg p-3">
        <h4 className="text-sm font-medium text-gray-400 mb-2">Latest Chatter</h4>
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {Object.values(data.sources || {}).flatMap(s =>
            (s.sample_posts || []).map((post, i) => (
              <div key={`${s.source}-${i}`} className="text-xs text-gray-300 p-2 bg-gray-900/50 rounded">
                <span className={`inline-block mr-1 px-1 py-0.5 rounded text-[10px] uppercase ${
                  post.sentiment === 'bullish' ? 'bg-green-900/50 text-green-400' : 'bg-red-900/50 text-red-400'
                }`}>
                  {s.source}
                </span>
                {post.text}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default memo(SentimentDashboard);

function SourceCard({ name, source }) {
  const color = SCORE_COLORS[source.label] || 'text-gray-400';
  return (
    <div className="bg-gray-800/50 rounded-lg p-3">
      <div className="text-xs text-gray-500 capitalize mb-1">{name}</div>
      <div className={`text-xl font-bold ${color}`}>
        {source.score > 0 ? '+' : ''}{source.score}
      </div>
      <div className={`text-xs ${color}`}>{source.label?.replace('_', ' ')}</div>
      {source.bullish_pct !== undefined && (
        <div className="mt-1">
          <div className="flex justify-between text-[10px] text-gray-500">
            <span className="text-green-400">{source.bullish_pct}% bull</span>
            <span className="text-red-400">{source.bearish_pct}% bear</span>
          </div>
          <div className="w-full h-1 bg-red-900/50 rounded mt-0.5">
            <div
              className="h-full bg-green-500 rounded"
              style={{ width: `${source.bullish_pct}%` }}
            />
          </div>
        </div>
      )}
      {source.post_count !== undefined && (
        <div className="text-[10px] text-gray-500 mt-1">{source.post_count} posts</div>
      )}
      {source.article_count !== undefined && (
        <div className="text-[10px] text-gray-500 mt-1">{source.article_count} articles</div>
      )}
    </div>
  );
}
