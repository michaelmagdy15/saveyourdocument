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
  Save,
  Loader2,
  Undo2,
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

export default function TextPreview({ 
  originalText = MOCK_ORIGINAL, 
  humanizedText = MOCK_HUMANIZED,
  onSaveEdits = null,
  isSaving = false
}) {
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'unified' | 'clean'
  const [copied, setCopied] = useState(false);
  const [showToast, setShowToast] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  // Editable paragraphs state
  const [editedParagraphs, setEditedParagraphs] = useState([]);
  const [editingIndex, setEditingIndex] = useState(-1);

  // Synchronize internal state with incoming humanized text prop
  useEffect(() => {
    if (humanizedText) {
      setEditedParagraphs(humanizedText.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean));
    } else {
      setEditedParagraphs([]);
    }
  }, [humanizedText]);

  // Split original paragraphs
  const originalParagraphs = originalText ? originalText.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean) : [];
  const maxParagraphs = Math.max(originalParagraphs.length, editedParagraphs.length);

  // Copy to Clipboard trigger
  const handleCopy = () => {
    navigator.clipboard.writeText(editedParagraphs.join("\n\n"));
    setCopied(true);
    setToastMessage('Humanized text copied to clipboard successfully!');
    setShowToast(true);
  };

  // Revert all edits back to original generated humanized text
  const handleRevert = () => {
    if (window.confirm("Are you sure you want to discard all your manual edits and revert to the original humanized version?")) {
      setEditedParagraphs(humanizedText.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean));
      setEditingIndex(-1);
      setToastMessage('Reverted to original humanized text.');
      setShowToast(true);
    }
  };

  // Save manual edits to backend
  const handleSave = async () => {
    if (onSaveEdits) {
      await onSaveEdits(editedParagraphs.join("\n\n"));
      setToastMessage('Edits applied and recompiled into Word document successfully!');
      setShowToast(true);
    }
  };

  useEffect(() => {
    if (showToast) {
      const timer = setTimeout(() => {
        setCopied(false);
        setShowToast(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [showToast]);

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

  // Detect whether user edits are different from original humanized text
  const isModified = editedParagraphs.join("\n\n") !== humanizedText;

  return (
    <div className="diff-viewer-container">
      {/* Dashboard & Preview Toolbar */}
      <div className="diff-viewer-header">
        <div className="diff-viewer-title">
          <h3>
            <FileText size={18} style={{ color: 'var(--purple-accent)' }} />
            Compare & Live Edit Transformations
          </h3>
          <p>Double-click any paragraph in the Optimized Human column or Clean view to edit in-place</p>
        </div>

        <div className="diff-controls">
          {/* Toggles for layout modes */}
          <div className="diff-view-selector">
            <button
              className={`diff-view-btn ${viewMode === 'split' ? 'active' : ''}`}
              onClick={() => setViewMode('split')}
              title="Compare side-by-side paragraphs and edit"
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
              title="Show clean final output and edit"
            >
              <Eye size={14} />
              Clean Text
            </button>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            {isModified && (
              <button className="diff-view-btn" onClick={handleRevert} title="Discard edits">
                <Undo2 size={14} />
                <span>Revert</span>
              </button>
            )}

            {onSaveEdits && isModified && (
              <button 
                className="diff-save-btn" 
                onClick={handleSave} 
                disabled={isSaving}
                title="Save manual edits and rebuild Word document"
              >
                {isSaving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                <span>{isSaving ? 'Saving...' : 'Apply Edits'}</span>
              </button>
            )}

            <button className="diff-copy-btn" onClick={handleCopy}>
              {copied ? <Check size={14} /> : <Copy size={14} />}
              <span>{copied ? 'Copied!' : 'Copy Clean'}</span>
            </button>
          </div>
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
                  Optimized Human Text (Editable)
                </span>
              </div>
            </div>

            {Array.from({ length: maxParagraphs }).map((_, idx) => {
              const origPara = originalParagraphs[idx] || '';
              const humanPara = editedParagraphs[idx] || '';
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

                  {/* Humanized text block - double click to edit */}
                  <div className="diff-column humanized">
                    <span className="diff-col-badge humanized">
                      <Sparkles size={13} />
                      Optimized Human Text
                    </span>
                    
                    {editingIndex === idx ? (
                      <div className="paragraph-edit-box">
                        <textarea
                          value={humanPara}
                          onChange={(e) => {
                            const updated = [...editedParagraphs];
                            updated[idx] = e.target.value;
                            setEditedParagraphs(updated);
                          }}
                          onBlur={() => setEditingIndex(-1)}
                          onKeyDown={(e) => {
                            // Finish editing on Ctrl+Enter or Esc
                            if ((e.key === 'Enter' && e.ctrlKey) || e.key === 'Escape') {
                              setEditingIndex(-1);
                            }
                          }}
                          autoFocus
                          className="premium-paragraph-textarea"
                          placeholder="Type paragraph text here..."
                        />
                        <div className="paragraph-edit-actions">
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                            Press <kbd style={{ background: '#1e293b', padding: '1px 4px', borderRadius: '3px' }}>Ctrl + Enter</kbd> or click outside to finish editing
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div 
                        onDoubleClick={() => setEditingIndex(idx)} 
                        title="Double-click to edit this paragraph in-place"
                        className="editable-paragraph-preview"
                      >
                        <p>
                          {humanPara ? (
                            renderColumnText(paragraphDiff, 'humanized')
                          ) : (
                            <span className="text-xs italic" style={{ color: 'var(--text-muted)', opacity: 0.7 }}>
                              (Paragraph is empty. Double-click to type.)
                            </span>
                          )}
                        </p>
                        <span className="edit-indicator-icon">✎</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* CASE 2: Unified Inline Diff (GitHub Style) */}
        {viewMode === 'unified' && (
          <div className="unified-diff-container">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0.25rem 0.5rem 0.75rem', borderBottom: '1px dashed var(--border-glass)', marginBottom: '0.5rem' }}>
              <AlertCircle size={14} style={{ color: 'var(--purple-accent)' }} />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Inline Diff mode displays character comparison. To manually edit paragraphs, please switch to <strong>Split Columns</strong> or <strong>Clean Text</strong>.
              </span>
            </div>
            {Array.from({ length: maxParagraphs }).map((_, idx) => {
              const origPara = originalParagraphs[idx] || '';
              const humanPara = editedParagraphs[idx] || '';
              const paragraphDiff = diffWords(origPara, humanPara);

              return (
                <div key={idx} className="unified-paragraph">
                  <p>{renderUnifiedText(paragraphDiff)}</p>
                </div>
              );
            })}
          </div>
        )}

        {/* CASE 3: Clean Read Mode (Editable) */}
        {viewMode === 'clean' && (
          <div className="clean-view-container">
            {editedParagraphs.map((para, idx) => (
              <div key={idx} className="clean-paragraph">
                {editingIndex === idx ? (
                  <div className="paragraph-edit-box">
                    <textarea
                      value={para}
                      onChange={(e) => {
                        const updated = [...editedParagraphs];
                        updated[idx] = e.target.value;
                        setEditedParagraphs(updated);
                      }}
                      onBlur={() => setEditingIndex(-1)}
                      onKeyDown={(e) => {
                        if ((e.key === 'Enter' && e.ctrlKey) || e.key === 'Escape') {
                          setEditingIndex(-1);
                        }
                      }}
                      autoFocus
                      className="premium-paragraph-textarea"
                    />
                    <div className="paragraph-edit-actions">
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        Press <kbd style={{ background: '#1e293b', padding: '1px 4px', borderRadius: '3px' }}>Ctrl + Enter</kbd> or click outside to finish editing
                      </span>
                    </div>
                  </div>
                ) : (
                  <div 
                    onDoubleClick={() => setEditingIndex(idx)} 
                    title="Double-click to edit this paragraph in-place"
                    className="editable-paragraph-preview"
                  >
                    <p>{para}</p>
                    <span className="edit-indicator-icon">✎</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Toast Notification */}
      {showToast && (
        <div className="copy-toast">
          <Sparkles size={16} />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}
