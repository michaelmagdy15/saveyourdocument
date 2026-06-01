import { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import ProgressBar from './components/ProgressBar';
import Dashboard from './components/Dashboard';
import TextPreview from './components/TextPreview';
import { Sparkles, Heart, ShieldCheck, Key, RefreshCw, UploadCloud, Eye, EyeOff, Lock, Loader2 } from 'lucide-react';
import './App.css';

// Auto-detect API base: in production (Cloud Run), frontend and backend share the same origin.
// In development, the backend runs on localhost:8000.
const API_BASE = window.location.port === '5173' ? 'http://localhost:8000' : '';

export default function App() {
  // --- STATE ---
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('syd_api_key') || '');
  const [showApiKey, setShowApiKey] = useState(false);
  const [isApiKeySaved, setIsApiKeySaved] = useState(() => !!localStorage.getItem('syd_api_key'));
  
  // Connection state (detecting, live, demo)
  const [connectionMode, setConnectionMode] = useState('detecting'); 
  
  // Processing states
  const [processingStatus, setProcessingStatus] = useState('idle'); // idle, uploading, humanizing, completed, error
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [activeStep, setActiveStep] = useState(1); // 1: Upload, 2: Process, 3: Dashboard

  // Data states
  const [file, setFile] = useState(null);
  const [fileId, setFileId] = useState('');
  const [beforeMetrics, setBeforeMetrics] = useState(null);
  const [afterMetrics, setAfterMetrics] = useState(null);
  const [originalSnippet, setOriginalSnippet] = useState('');
  const [humanizedSnippet, setHumanizedSnippet] = useState('');

  // --- COMPATIBILITY CONNECTION CHECK ---
  useEffect(() => {
    // Check if the FastAPI backend is running by pinging its root or upload endpoint
    const checkBackend = async () => {
      try {
        const res = await fetch(`${API_BASE}/`, { method: 'GET' });
        if (res.ok) {
          setConnectionMode('live');
          console.log("Connected to SAVEYOURDOCUMENT backend.");
        } else {
          setConnectionMode('demo');
          console.warn("Backend returned non-200. Defaulting to Demo Mode.");
        }
      } catch {
        setConnectionMode('demo');
        console.warn("Backend offline. Defaulting to Demo Mode.");
      }
    };
    checkBackend();
  }, []);

  // --- API KEY ACTIONS ---
  const handleSaveApiKey = (e) => {
    e.preventDefault();
    if (apiKey.trim()) {
      localStorage.setItem('syd_api_key', apiKey.trim());
      setIsApiKeySaved(true);
    }
  };

  const handleClearApiKey = () => {
    localStorage.removeItem('syd_api_key');
    setApiKey('');
    setIsApiKeySaved(false);
  };

  // --- INGEST / UPLOAD HANDLER ---
  const handleFileUpload = async (selectedFile) => {
    setFile(selectedFile);
    setProcessingStatus('uploading');
    setProgress(10);
    setStatusMessage('Uploading Word document to secure server...');
    setErrorMessage('');
    
    if (connectionMode === 'live') {
      const formData = new FormData();
      formData.append('file', selectedFile);

      try {
        const response = await fetch(`${API_BASE}/api/upload`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || 'Failed to upload document.');
        }

        const data = await response.json();
        setFileId(data.file_id);
        setBeforeMetrics(data.metrics);
        setProcessingStatus('idle');
        setProgress(0);
        setStatusMessage('Document uploaded and metrics pre-calculated. Ready to humanize.');
        setActiveStep(2); // Go to Processing Step
      } catch (err) {
        setErrorMessage(err.message || 'Error uploading document.');
        setProcessingStatus('error');
      }
    } else {
      // --- DEMO MODE INGEST SIMULATION ---
      setTimeout(() => {
        setFileId('demo_stage_report_' + Math.floor(Math.random() * 10000));
        // Mock a 7880-word docx report
        setBeforeMetrics({
          word_count: 7880,
          sentence_count: 421,
          readability_score: 34.2,
          ai_score: 94.0,
          human_score: 6.0,
          grade_level: 'Graduate (Extremely Complex)',
          vocabulary_richness: 0.38
        });
        setProcessingStatus('idle');
        setProgress(0);
        setStatusMessage('Document uploaded in demo mode. Ready to humanize.');
        setActiveStep(2);
      }, 1500);
    }
  };

  // --- REPHRASING / HUMANIZING HANDLER ---
  const handleStartHumanize = async () => {
    if (!fileId) return;
    setProcessingStatus('humanizing');
    setProgress(0);
    setStatusMessage('Starting deep rephrasing and plagiarism extraction...');

    if (connectionMode === 'live') {
      try {
        const response = await fetch(`${API_BASE}/api/humanize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            file_id: fileId,
            api_key: apiKey || null
          })
        });

        if (!response.ok) {
          const errData = await response.json();
          throw new Error(errData.detail || 'Failed to start humanization.');
        }

        // Read SSE chunk-by-chunk stream using standard ReadableStream
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop(); // Keep incomplete line

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6);
              try {
                const event = jsonParseSafe(dataStr);
                if (!event) continue;

                if (event.status === 'processing') {
                  setProgress(event.progress_percentage);
                  setStatusMessage(`Processing chunk ${event.current_chunk} of ${event.total_chunks}...`);
                  setOriginalSnippet(event.original_text);
                  setHumanizedSnippet(event.humanized_text);
                } else if (event.status === 'completed') {
                  setProgress(100);
                  setStatusMessage('Document rephrased and compiled successfully.');
                  setAfterMetrics({
                    word_count: event.metrics.word_count,
                    sentence_count: event.metrics.sentence_count,
                    readability_score: event.metrics.readability_score,
                    ai_score: event.metrics.ai_score,
                    human_score: event.metrics.human_score,
                    grade_level: event.metrics.grade_level,
                    vocabulary_richness: event.metrics.vocabulary_richness
                  });
                  setProcessingStatus('completed');
                  setActiveStep(3); // Go to Dashboard Step
                } else if (event.status === 'error') {
                  throw new Error(event.message || 'API parsing exception.');
                }
              } catch (e) {
                console.error("Error parsing stream event:", e);
              }
            }
          }
        }
      } catch (err) {
        setErrorMessage(err.message || 'An error occurred during humanization.');
        setProcessingStatus('error');
      }
    } else {
      // --- DEMO MODE SSE SIMULATION ---
      const mockChunks = [
        { orig: "En conclusion, il convient de souligner que l'analyse des résultats démontre de surcroît l'efficacité de cette technologie.", hum: "Pour conclure, l'analyse des résultats met en évidence à quel point cette technologie s'avère particulièrement efficace." },
        { orig: "De plus, il est important de noter que les collaborateurs ont fait preuve d'une adaptation rapide et proactive en effet.", hum: "Par ailleurs, on remarque que l'équipe s'est adaptée avec une rapidité et une réactivité exemplaires." },
        { orig: "En résumé, il convient de rappeler que la formation continue constitue un facteur clé de réussite absolue.", hum: "En définitive, rappelons que l'apprentissage continu demeure le levier principal de notre réussite." }
      ];

      let chunkIdx = 0;
      const interval = setInterval(() => {
        chunkIdx++;
        const pct = Math.round((chunkIdx / 10) * 100);
        setProgress(pct);
        setStatusMessage(`Processing French chunk ${chunkIdx} of 10 (7,880 words total)...`);
        
        const mockIdx = (chunkIdx - 1) % mockChunks.length;
        setOriginalSnippet(mockChunks[mockIdx].orig);
        setHumanizedSnippet(mockChunks[mockIdx].hum);

        if (chunkIdx >= 10) {
          clearInterval(interval);
          setProgress(100);
          setStatusMessage('Document rephrased and compiled successfully.');
          // Humanized statistics
          setAfterMetrics({
            word_count: 7912,
            sentence_count: 458,
            readability_score: 68.5,
            ai_score: 4.0,
            human_score: 96.0,
            grade_level: 'Facile (Niveau collège)',
            vocabulary_richness: 0.54
          });
          setProcessingStatus('completed');
          setActiveStep(3);
        }
      }, 800);
    }
  };

  // --- DOWNLOAD HANDLER ---
  const handleDownload = () => {
    if (connectionMode === 'live') {
      window.open(`${API_BASE}/api/download/${fileId}`, '_blank');
    } else {
      // Demo Mode file trigger download
      const element = document.createElement("a");
      const fileContent = `--- DEMO MODE HUMANIZED DOCUMENT ---\n\n` + 
        `Document ID: ${fileId}\n` +
        `Word Count: ${afterMetrics.word_count}\n` +
        `AI Detection Probability: ${afterMetrics.ai_score}%\n` +
        `Linguistic Score Improvements: ${beforeMetrics.readability_score} -> ${afterMetrics.readability_score}\n\n` +
        `French stage report rephrased successfully!`;
      const fileData = new Blob([fileContent], {type: 'text/plain'});
      element.href = URL.createObjectURL(fileData);
      element.download = "humanized_rapport_de_stage.txt";
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    }
  };

  // --- RESET HANDLER ---
  const handleReset = () => {
    setFile(null);
    setFileId('');
    setBeforeMetrics(null);
    setAfterMetrics(null);
    setOriginalSnippet('');
    setHumanizedSnippet('');
    setProcessingStatus('idle');
    setProgress(0);
    setStatusMessage('');
    setErrorMessage('');
    setActiveStep(1);
  };

  const jsonParseSafe = (str) => {
    try {
      return JSON.parse(str);
    } catch {
      return null;
    }
  };

  return (
    <div className="app-workspace">
      {/* Premium Hero Title and Navigation */}
      <header className="app-header">
        <div className="header-brand">
          <div className="glow-logo">
            <Sparkles size={24} style={{ color: 'var(--accent)' }} />
          </div>
          <div>
            <h2>SAVEYOURDOCUMENT</h2>
            <p>AI Document Humanizer & Plagiarism Shield</p>
          </div>
        </div>
        
        {/* Dynamic connection indicator */}
        <div className="header-actions">
          <div className={`status-badge ${connectionMode}`}>
            <span className="pulse-indicator"></span>
            <span>{connectionMode === 'live' ? 'Live Server Connected' : connectionMode === 'demo' ? 'Local Demo Mode' : 'Detecting Connection...'}</span>
          </div>
        </div>
      </header>

      {/* Main Layout Area */}
      <main className="main-content-layout">
        
        {/* API Key Panel - Glassmorph Row */}
        <div className="api-config-bar">
          <div className="api-config-title">
            <Key size={18} className="text-indigo-400" />
            <span>Gemini API Configuration</span>
          </div>
          
          {isApiKeySaved ? (
            <div className="api-key-saved-container">
              <span className="api-key-status-text">
                <ShieldCheck size={16} />
                <span>API Key Loaded securely</span>
              </span>
              <button className="api-key-btn-lock" onClick={handleClearApiKey}>
                <Lock size={12} />
                <span>Lock / Remove</span>
              </button>
            </div>
          ) : (
            <form onSubmit={handleSaveApiKey} className="api-key-form">
              <div className="api-key-input-container">
                <input
                  type={showApiKey ? "text" : "password"}
                  placeholder="Enter Gemini API Key..."
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="api-key-input"
                />
                <button
                  type="button"
                  className="api-key-btn-show"
                  onClick={() => setShowApiKey(!showApiKey)}
                  title={showApiKey ? "Hide API Key" : "Show API Key"}
                >
                  {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <button type="submit" className="api-key-btn-submit">
                Apply Key
              </button>
            </form>
          )}
        </div>

        {/* Steps Flow Controls */}
        <div className="steps-timeline-container glass-panel mb-6">
          <div className="steps-timeline">
            
            {/* Step 1: Upload */}
            <div className={`step-node ${activeStep === 1 ? 'active' : 'completed'}`}>
              <div className="step-badge">1</div>
              <span className="step-label">Upload</span>
            </div>
            
            {/* Connector 1-2 */}
            <div className={`step-connector ${activeStep >= 2 ? 'active' : ''}`}></div>
            
            {/* Step 2: Humanize */}
            <div className={`step-node ${activeStep === 2 ? 'active' : activeStep > 2 ? 'completed' : 'inactive'}`}>
              <div className="step-badge">2</div>
              <span className="step-label">Humanize</span>
            </div>
            
            {/* Connector 2-3 */}
            <div className={`step-connector ${activeStep >= 3 ? 'active' : ''}`}></div>
            
            {/* Step 3: Analytics */}
            <div className={`step-node ${activeStep === 3 ? 'active' : activeStep > 3 ? 'completed' : 'inactive'}`}>
              <div className="step-badge">3</div>
              <span className="step-label">Analytics</span>
            </div>

          </div>
        </div>

        {/* Dynamic Panels according to active steps */}
        
        {/* Step 1: File Upload */}
        {activeStep === 1 && (
          <section className="upload-panel-container">
            <div className="upload-panel-header">
              <div className="upload-panel-icon-wrapper animate-subtle">
                <UploadCloud size={32} />
              </div>
              <h2 className="upload-panel-title">Remove AI Plagiarism in French</h2>
              <p className="upload-panel-description">
                Ingest your French reports, articles, or stage documents. Our system will analyze, rephrase, and rebuild the `.docx` document keeping all styling intact.
              </p>
            </div>
            
            <div className="upload-panel-component-wrapper">
              <FileUpload
                onFileSelect={(f) => setFile(f)}
                onUpload={handleFileUpload}
                isUploading={processingStatus === 'uploading'}
                externalError={errorMessage}
              />
            </div>

            {/* Special Sample Option */}
            <div className="upload-panel-footer">
              <span className="upload-panel-footer-text">Don&apos;t have your French file handy?</span>
              <button 
                className="upload-panel-sample-btn"
                onClick={() => {
                  // Pre-load mock french stage report
                  handleFileUpload({
                    name: 'el_rapport_de_stage.docx',
                    size: 154820
                  });
                }}
              >
                Load Sample Stage Report (7,880 words)
              </button>
            </div>
          </section>
        )}

        {/* Step 2: Processing */}
        {activeStep === 2 && (
          <section className="process-panel-container glass-panel animate-fade-in">
            <div className="process-panel-header">
              <div className="process-header-info">
                <h3>Document Processing</h3>
                <p>Ingested: <span className="highlight-filename">{file?.name}</span></p>
              </div>
              
              <button className="process-reset-btn" onClick={handleReset}>
                <RefreshCw size={12} />
                <span>Reset</span>
              </button>
            </div>

            {/* File metadata cards */}
            {beforeMetrics && (
              <div className="metadata-grid">
                <div className="metadata-card">
                  <span className="metadata-label">Total Words</span>
                  <span className="metadata-value">{beforeMetrics.word_count.toLocaleString()}</span>
                </div>
                <div className="metadata-card highlight-danger">
                  <span className="metadata-label">AI Plagiarism</span>
                  <span className="metadata-value text-danger">{beforeMetrics.ai_score}%</span>
                </div>
                <div className="metadata-card">
                  <span className="metadata-label">Readability</span>
                  <span className="metadata-value">{beforeMetrics.readability_score.toFixed(1)}</span>
                </div>
              </div>
            )}

            {/* Glowing progress visual */}
            <div className="progress-bar-wrapper">
              <ProgressBar
                progress={progress}
                status={statusMessage}
                isCompleted={processingStatus === 'completed'}
                hasError={processingStatus === 'error'}
              />
            </div>

            {/* Error Alert Banner */}
            {processingStatus === 'error' && errorMessage && (
              <div className="alert-error" role="alert">
                <strong>Error:</strong> {errorMessage}
              </div>
            )}

            {/* Snippet Live Previewer */}
            {(originalSnippet || humanizedSnippet) && (
              <div className="preview-box">
                <span className="preview-title">
                  <Sparkles size={12} style={{ color: 'var(--accent)' }} />
                  <span>Live Rephrasing Snippet Stream</span>
                </span>
                <div className="preview-grid">
                  <div className="preview-col original">
                    <span className="preview-col-title">Original Draft</span>
                    <p>{originalSnippet}</p>
                  </div>
                  <div className="preview-col humanized">
                    <span className="preview-col-title">Humanized</span>
                    <p>{humanizedSnippet}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Run button */}
            {processingStatus !== 'completed' && (
              <div className="run-btn-container">
                {processingStatus === 'humanizing' ? (
                  <button className="run-btn processing" disabled>
                    <span className="spin-icon"><Loader2 size={16} /></span>
                    <span>Processing...</span>
                  </button>
                ) : (
                  <button
                    onClick={handleStartHumanize}
                    className="run-btn"
                  >
                    <Sparkles size={16} />
                    <span>Start Humanization & Bypass AI</span>
                  </button>
                )}
              </div>
            )}
          </section>
        )}

        {/* Step 3: Results Dashboard */}
        {activeStep === 3 && beforeMetrics && afterMetrics && (
          <section className="animate-fade-in space-y-6">
            
            {/* Header Dashboard Controller */}
            <div className="download-panel glass-panel">
              <div className="download-title-area">
                <h3>
                  <ShieldCheck size={20} style={{ color: 'var(--emerald-accent, #10b981)' }} />
                  <span>Auditor Report & In-Place Download</span>
                </h3>
                <p>
                  Rephrasing completed. Structure, tables, list bullet indices, and drawings are preserved.
                </p>
              </div>
              <div className="download-actions-group">
                <button className="btn-secondary" onClick={handleReset}>
                  Process Another File
                </button>
                <button className="btn-primary" onClick={handleDownload}>
                  Download Humanized Word Doc
                </button>
              </div>
            </div>

            {/* Dashboard Graphs */}
            <Dashboard 
              stats={{
                humanScoreBefore: beforeMetrics.human_score,
                humanScoreAfter: afterMetrics.human_score,
                aiScoreBefore: beforeMetrics.ai_score,
                aiScoreAfter: afterMetrics.ai_score,
                vocabBefore: Math.round(beforeMetrics.vocabulary_richness * 100),
                vocabAfter: Math.round(afterMetrics.vocabulary_richness * 100),
                readEaseBefore: beforeMetrics.readability_score,
                readEaseAfter: afterMetrics.readability_score,
                wordCountOriginal: beforeMetrics.word_count,
                wordCountHumanized: afterMetrics.word_count,
                gradeBefore: beforeMetrics.grade_level,
                gradeAfter: afterMetrics.grade_level
              }}
            />

            {/* Side-by-side highlighter */}
            <TextPreview 
              originalText={originalSnippet || "En conclusion, il convient de souligner que l'analyse des résultats démontre de surcroît l'efficacité de cette technologie."} 
              humanizedText={humanizedSnippet || "Pour conclure, l'analyse des résultats met en évidence à quel point cette technologie s'avère particulièrement efficace."} 
            />

          </section>
        )}

      </main>

      {/* Footer */}
      <footer className="app-footer mt-12">
        <div className="footer-content">
          <span>SAVEYOURDOCUMENT • Powered by Mitrixo Systems</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            Made by Mitrixo Systems with <Heart size={12} fill="#ef4444" stroke="#ef4444" />
          </span>
        </div>
      </footer>
    </div>
  );
}