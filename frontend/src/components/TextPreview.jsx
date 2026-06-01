import { useState, useEffect } from 'react';
import {
  Columns,
  Layers,
  Eye,
  Copy,
  Check,
  FileText,
  Sparkles,
  AlertCircle,
} from 'lucide-react';
import './TextPreview.css';

// Default premium demo content to demonstrate the capability out of the box
const MOCK_ORIGINAL = `In this modern era of technology, it is important to note that artificial intelligence is becoming increasingly popular. It is utilized by many people to perform a variety of tasks. Many benefits are provided by this system, and efficiency is increased. However, caution must be exercised because errors can sometimes be made by the system.

Furthermore, it should be understood that writing produced by AI tools often lacks a certain level of human touch, personality, and emotional expression. Therefore, editing is required in order to make it sound natural and appealing to readers.`;

const MOCK_HUMANIZED = `Technology is advancing at breakneck speed, pushing artificial intelligence from the fringes straight into our daily routines. Millions of creators now rely on it every day to streamline their work and spark fresh ideas. But while these neural networks are incredibly powerful, we can't blindly trust them—they still trip over basic logic and require human oversight.

Let's face it: standard AI writing feels flat, robotic, and empty. It lacks the pulse of human emotion, the rhythm of authentic storytelling, and a distinct voice. That's why we need to rewrite and inject personality into it, transforming dry output into copy that actually connects with real readers.`;

/**
 * Custom LCS (Longest Common Subsequence) based Word Diff Algorithm
 * Splitting by regex /(\s+)/ keeps spaces as distinct array elements,
 * allowing us to rebuild strings with correct spacing and punctuation.
 */
function diffWords(originalStr, humanizedStr) {
  if (!originalStr) return [{ type: 'added', text: humanizedStr }];
  if (!humanizedStr) return [{ type: 'deleted', text: originalStr }];

  const w1 = originalStr.split(/(\s+)/);
  const w2 = humanizedStr.split(/(\s+)/);

  // Dynamic programming LCS matrix
  const dp = Array(w1.length + 1)
    .fill(null)
    .map(() => Array(w2.length + 1).fill(0));

  for (let idx1 = 1; idx1 <= w1.length; idx1++) {
    for (let idx2 = 1; idx2 <= w2.length; idx2++) {
      if (w1[idx1 - 1] === w2[idx2 - 1]) {
        dp[idx1][idx2] = dp[idx1 - 1][idx2 - 1] + 1;
      } else {
        dp[idx1][idx2] = Math.max(dp[idx1 - 1][idx2], dp[idx1][idx2 - 1]);
      }
    }
  }

  // Backtracking differences
  let i = w1.length;
  let j = w2.length;
  const result = [];

  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && w1[i - 1] === w2[j - 1]) {
      result.push({ type: 'unchanged', text: w1[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.push({ type: 'added', text: w2[j - 1] });
      j--;
    } else if (i > 0 && (j === 0 || dp[i][j - 1] < dp[i - 1][j])) {
      result.push({ type: 'deleted', text: w1[i - 1] });
      i--;
    }
  }

  return result.reverse();
}

export default function TextPreview({ originalText = MOCK_ORIGINAL, humanizedText = MOCK_HUMANIZED }) {
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'unified' | 'clean'
  const [copied, setCopied] = useState(false);
  const [showToast, setShowToast] = useState(false);

  // Split paragraphs and trim whitespace
  const originalParagraphs = originalText ? originalText.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean) : [];
  const humanizedParagraphs = humanizedText ? humanizedText.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean) : [];

  const maxParagraphs = Math.max(originalParagraphs.length, humanizedParagraphs.length);

  // Copy to Clipboard trigger
  const handleCopy = () => {
    navigator.clipboard.writeText(humanizedText);
    setCopied(true);
    setShowToast(true);
  };

  useEffect(() => {
    if (copied) {
      const timer = setTimeout(() => {
        setCopied(false);
        setShowToast(false);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [copied]);

  // Renders highlighted text segments for columns
  const renderColumnText = (diff, mode) => {
    return diff.map((chunk, index) => {
      if (chunk.type === 'unchanged') {
        return (
          <span key={index} className="word-normal">
            {chunk.text}
          </span>
        );
      }
      
      if (chunk.type === 'deleted' && mode === 'original') {
        return (
          <span key={index} className="word-deleted" title="Removed / Rewritten">
            {chunk.text}
          </span>
        );
      }
      
      if (chunk.type === 'added' && mode === 'humanized') {
        return (
          <span key={index} className="word-added" title="Added for flow / vocabulary">
            {chunk.text}
          </span>
        );
      }

      return null;
    });
  };

  // Renders a unified paragraph flow with inline deletions and additions
  const renderUnifiedText = (diff) => {
    return diff.map((chunk, index) => {
      if (chunk.type === 'unchanged') {
        return (
          <span key={index} className="word-normal">
            {chunk.text}
          </span>
        );
      }
      
      if (chunk.type === 'deleted') {
        return (
          <span key={index} className="word-deleted" title="Original wording">
            {chunk.text}
          </span>
        );
      }
      
      if (chunk.type === 'added') {
        return (
          <span key={index} className="word-added" title="Humanized wording">
            {chunk.text}
          </span>
        );
      }

      return null;
    });
  };

  return (
    <div className="diff-viewer-container">
      {/* Dashboard & Preview Toolbar */}
      <div className="diff-viewer-header">
        <div className="diff-viewer-title">
          <h3>
            <FileText size={18} style={{ color: 'var(--purple-accent)' }} />
            Compare Writing Transformations
          </h3>
          <p>Examine stylistic polishing, structural flow corrections, and vocabulary shifts</p>
        </div>

        <div className="diff-controls">
          {/* Toggles for layout modes */}
          <div className="diff-view-selector">
            <button
              className={`diff-view-btn ${viewMode === 'split' ? 'active' : ''}`}
              onClick={() => setViewMode('split')}
              title="Compare side-by-side paragraphs"
            >
              <Columns size={14} />
              Split Columns
            </button>
            <button
              className={`diff-view-btn ${viewMode === 'unified' ? 'active' : ''}`}
              onClick={() => setViewMode('unified')}
              title="Show changes inline"
            >
              <Layers size={14} />
              Inline Diff
            </button>
            <button
              className={`diff-view-btn ${viewMode === 'clean' ? 'active' : ''}`}
              onClick={() => setViewMode('clean')}
              title="Show clean final output"
            >
              <Eye size={14} />
              Clean Text
            </button>
          </div>

          {/* Copy Button */}
          <button className="diff-copy-btn" onClick={handleCopy}>
            {copied ? <Check size={14} /> : <Copy size={14} />}
            <span>{copied ? 'Copied!' : 'Copy Clean'}</span>
          </button>
        </div>
      </div>

      {/* Main Diff Content Container */}
      <div className="diff-content-wrapper">
        {/* CASE 1: Split Side-by-Side Paragraphs View */}
        {viewMode === 'split' && (
          <div className="diff-grid">
            <div className="diff-labels-row">
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span className="diff-col-badge original">
                  <AlertCircle size={13} />
                  Original AI Draft
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span className="diff-col-badge humanized">
                  <Sparkles size={13} />
                  Optimized Human Text
                </span>
              </div>
            </div>

            {Array.from({ length: maxParagraphs }).map((_, idx) => {
              const origPara = originalParagraphs[idx] || '';
              const humanPara = humanizedParagraphs[idx] || '';
              const paragraphDiff = diffWords(origPara, humanPara);

              return (
                <div key={idx} className="diff-row">
                  {/* Original text block with deletions */}
                  <div className="diff-column original">
                    <span className="diff-col-badge original">
                      <AlertCircle size={13} />
                      Original AI Draft
                    </span>
                    <p>
                      {origPara ? (
                        renderColumnText(paragraphDiff, 'original')
                      ) : (
                        <span className="text-xs italic" style={{ color: 'var(--text-muted)', opacity: 0.7 }}>
                          (No original paragraph at this index)
                        </span>
                      )}
                    </p>
                  </div>

                  {/* Humanized text block with insertions */}
                  <div className="diff-column humanized">
                    <span className="diff-col-badge humanized">
                      <Sparkles size={13} />
                      Optimized Human Text
                    </span>
                    <p>
                      {humanPara ? (
                        renderColumnText(paragraphDiff, 'humanized')
                      ) : (
                        <span className="text-xs italic" style={{ color: 'var(--text-muted)', opacity: 0.7 }}>
                          (No humanized paragraph at this index)
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* CASE 2: Unified Inline Diff (GitHub Style) */}
        {viewMode === 'unified' && (
          <div className="unified-diff-container">
            {Array.from({ length: maxParagraphs }).map((_, idx) => {
              const origPara = originalParagraphs[idx] || '';
              const humanPara = humanizedParagraphs[idx] || '';
              const paragraphDiff = diffWords(origPara, humanPara);

              return (
                <div key={idx} className="unified-paragraph">
                  <p>{renderUnifiedText(paragraphDiff)}</p>
                </div>
              );
            })}
          </div>
        )}

        {/* CASE 3: Clean Read Mode */}
        {viewMode === 'clean' && (
          <div className="clean-view-container">
            {humanizedParagraphs.map((para, idx) => (
              <div key={idx} className="clean-paragraph">
                <p>{para}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Copied Notification Toast */}
      {showToast && (
        <div className="copy-toast">
          <Sparkles size={16} />
          <span>Humanized text copied to clipboard successfully!</span>
        </div>
      )}
    </div>
  );
}

